"""
OpenStudio C++ Documentation Scraper

Scrapes OpenStudio 3.9.0 C++ documentation from S3 and extracts:
- Class names, namespaces, descriptions
- Method signatures, parameters, return types
- Parent class relationships
"""

import asyncio
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn

console = Console()


@dataclass
class MethodParameter:
    """Represents a method parameter"""

    name: Optional[str]
    param_type: str
    default_value: Optional[str] = None


@dataclass
class Method:
    """Represents a class method"""

    name: str
    signature: str
    return_type: str
    description: str
    parameters: List[MethodParameter]
    is_static: bool = False
    is_const: bool = False


@dataclass
class OpenStudioClass:
    """Represents an OpenStudio class"""

    name: str
    namespace: str
    full_name: str
    description: str
    parent_class: Optional[str]
    doc_url: str
    methods: List[Method]


class OpenStudioDocsScraper:
    """Scrapes OpenStudio C++ documentation from S3"""

    BASE_URL = "https://s3.amazonaws.com/openstudio-sdk-documentation/cpp/OpenStudio-3.9.0-doc/model/html/"
    VERSION = "3.9.0"

    def __init__(self, max_concurrent: int = 50, timeout: float = 30.0):
        self.max_concurrent = max_concurrent
        self.timeout = timeout
        self.client = None

    async def __aenter__(self):
        """Async context manager entry"""
        self.client = httpx.AsyncClient(timeout=self.timeout)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.client:
            await self.client.aclose()

    async def fetch_page(self, url: str) -> str:
        """Fetch a single page"""
        if not self.client:
            raise RuntimeError("Scraper not initialized. Use 'async with' context manager.")

        response = await self.client.get(url)
        response.raise_for_status()
        return response.text

    async def get_class_list(self) -> List[tuple[str, str]]:
        """
        Get list of all classes from the index page

        Returns:
            List of (class_name, class_url) tuples
        """
        console.print("[cyan]Fetching class list...[/cyan]")

        # Fetch the classes.html page
        classes_url = urljoin(self.BASE_URL, "classes.html")
        html = await self.fetch_page(classes_url)

        soup = BeautifulSoup(html, "lxml")

        # Find all class links
        # Classes are in <a class="el"> links that start with "classopenstudio"
        classes = []
        for link in soup.find_all("a", class_="el"):
            href = link.get("href")
            if href and href.startswith("classopenstudio"):
                class_url = urljoin(self.BASE_URL, href)
                # Extract class name from link text
                class_name = link.text.strip()
                # Avoid duplicates
                if (class_name, class_url) not in classes:
                    classes.append((class_name, class_url))

        console.print(f"[green]Found {len(classes)} classes[/green]")
        return classes

    def parse_class_page(self, html: str, class_url: str) -> Optional[OpenStudioClass]:
        """
        Parse a single class documentation page

        Args:
            html: HTML content of the class page
            class_url: URL of the class page

        Returns:
            OpenStudioClass object or None if parsing failed
        """
        soup = BeautifulSoup(html, "lxml")

        # Extract class name and namespace from title
        title_elem = soup.find("div", class_="title")
        if not title_elem:
            return None

        title = title_elem.text.strip()
        # Example: "openstudio::model::ThermalZone Class Reference"
        match = re.match(r"(.+?)\s+Class Reference", title)
        if not match:
            return None

        full_name = match.group(1)
        parts = full_name.split("::")
        name = parts[-1] if parts else full_name
        namespace = "::".join(parts[:-1]) if len(parts) > 1 else ""

        # Extract description
        description = ""
        textblock = soup.find("div", class_="textblock")
        if textblock:
            # Get first paragraph
            first_p = textblock.find("p")
            if first_p:
                description = first_p.get_text(strip=True)

        # Extract parent class
        parent_class = None
        inheritance = soup.find("div", class_="inheritance")
        if inheritance:
            # Look for parent class links
            links = inheritance.find_all("a")
            if links:
                # Usually the direct parent is the last link before current class
                for link in links:
                    link_text = link.text.strip()
                    if link_text != name and "::" in link_text:
                        parent_class = link_text.split("::")[-1]

        # Extract methods
        methods = self._parse_methods(soup)

        return OpenStudioClass(
            name=name,
            namespace=namespace,
            full_name=full_name,
            description=description,
            parent_class=parent_class,
            doc_url=class_url,
            methods=methods,
        )

    def _parse_methods(self, soup: BeautifulSoup) -> List[Method]:
        """Parse all methods from the class page"""
        methods = []

        # Find method items (div class="memitem")
        for memitem in soup.find_all("div", class_="memitem"):
            memproto = memitem.find("div", class_="memproto")
            if not memproto:
                continue

            # Find the memname table which contains the method signature
            memname_table = memproto.find("table", class_="memname")
            if not memname_table:
                continue

            # Extract method signature from memname table
            # Structure: <td class="memname">return_type ClassName::methodName</td>
            #            <td>(</td>
            #            <td class="paramtype">param_type</td>
            #            <td class="paramname">param_name</td>
            #            <td>)</td>

            # Get method name from first td.memname
            memname_cell = memname_table.find("td", class_="memname")
            if not memname_cell:
                continue

            memname_text = memname_cell.get_text(strip=True)
            # Example: "openstudio::model::ThermalZone::ThermalZone"
            # Or: "boost::optional< Building > getBuilding"

            # Extract method name (last part after ::)
            parts = memname_text.split("::")
            if len(parts) > 1:
                method_name = parts[-1].strip()
            else:
                # No namespace, extract method name from text
                # Handle cases like "boost::optional< Building > getBuilding"
                tokens = memname_text.split()
                method_name = tokens[-1] if tokens else ""

            if not method_name:
                continue

            # Build return type (everything before method name in memname)
            return_type_match = re.match(r"(.+?)\s+\w+$", memname_text)
            return_type = return_type_match.group(1) if return_type_match else ""

            # Check for static/const
            is_static = "static" in memname_text.lower()
            is_const = False

            # Parse parameters from the table
            parameters = []
            param_types = memname_table.find_all("td", class_="paramtype")
            param_names = memname_table.find_all("td", class_="paramname")

            for param_type_cell, param_name_cell in zip(param_types, param_names):
                param_type = param_type_cell.get_text(strip=True)
                param_name_text = param_name_cell.get_text(strip=True)

                # Remove <em> tags content for parameter names
                param_name = param_name_text if param_name_text else None

                if param_type:
                    parameters.append(
                        MethodParameter(name=param_name, param_type=param_type, default_value=None)
                    )

            # Build full signature
            param_strs = []
            for p in parameters:
                if p.name:
                    param_strs.append(f"{p.param_type} {p.name}")
                else:
                    param_strs.append(p.param_type)
            signature = f"{memname_text}({', '.join(param_strs)})"

            # Check if const method (check for "const" after closing paren in the row)
            if memproto:
                text = memproto.get_text()
                if re.search(r"\)\s+const\s*$", text):
                    is_const = True

            # Get description from memdoc
            description = ""
            memdoc = memitem.find("div", class_="memdoc")
            if memdoc:
                # Get first paragraph
                first_p = memdoc.find("p")
                if first_p:
                    text = first_p.get_text(separator=" ", strip=True)
                    # Take up to first period or 200 chars
                    if "." in text:
                        description = text.split(".")[0] + "."
                    else:
                        description = text[:200]

            methods.append(
                Method(
                    name=method_name,
                    signature=signature,
                    return_type=return_type,
                    description=description,
                    parameters=parameters,
                    is_static=is_static,
                    is_const=is_const,
                )
            )

        return methods

    def _parse_parameters(self, signature: str) -> List[MethodParameter]:
        """
        Parse parameters from method signature

        Args:
            signature: Method signature string

        Returns:
            List of MethodParameter objects
        """
        # Extract parameter list from signature
        # Example: "bool setName(const std::string &name, int priority = 0)"
        match = re.search(r"\((.*?)\)(?:\s+const)?$", signature)
        if not match:
            return []

        param_str = match.group(1).strip()
        if not param_str or param_str == "void":
            return []

        parameters = []
        # Split by comma, but respect nested templates
        current_param = ""
        depth = 0
        for char in param_str + ",":
            if char in "<([":
                depth += 1
            elif char in ">)]":
                depth -= 1
            elif char == "," and depth == 0:
                if current_param.strip():
                    param = self._parse_single_parameter(current_param.strip())
                    if param:
                        parameters.append(param)
                current_param = ""
                continue
            current_param += char

        return parameters

    def _parse_single_parameter(self, param_str: str) -> Optional[MethodParameter]:
        """
        Parse a single parameter string

        Args:
            param_str: Parameter string (e.g., "const std::string &name")

        Returns:
            MethodParameter or None
        """
        # Check for default value
        default_value = None
        if "=" in param_str:
            parts = param_str.split("=", 1)
            param_str = parts[0].strip()
            default_value = parts[1].strip()

        # Extract type and name
        # Last word is usually the name, everything before is the type
        tokens = param_str.split()
        if not tokens:
            return None

        # Handle cases like "unsigned int value" or "const Type& name"
        if len(tokens) == 1:
            # Only type, no name
            return MethodParameter(name=None, param_type=param_str, default_value=default_value)

        # Last token is name (unless it's a reference/pointer symbol)
        param_name = tokens[-1]
        if param_name in ["&", "*", "const"]:
            # No name provided
            return MethodParameter(name=None, param_type=param_str, default_value=default_value)

        # Everything before last token is the type
        param_type = " ".join(tokens[:-1])

        return MethodParameter(name=param_name, param_type=param_type, default_value=default_value)

    async def scrape_class(self, class_name: str, class_url: str) -> Optional[OpenStudioClass]:
        """
        Scrape a single class page

        Args:
            class_name: Name of the class
            class_url: URL to the class documentation

        Returns:
            OpenStudioClass object or None if scraping failed
        """
        try:
            html = await self.fetch_page(class_url)
            return self.parse_class_page(html, class_url)
        except Exception as e:
            console.print(f"[red]Error scraping {class_name}: {e}[/red]")
            return None

    async def scrape_all_classes(self) -> List[OpenStudioClass]:
        """
        Scrape all OpenStudio classes

        Returns:
            List of OpenStudioClass objects
        """
        # Get class list
        class_list = await self.get_class_list()

        # Create semaphore to limit concurrency
        semaphore = asyncio.Semaphore(self.max_concurrent)

        async def scrape_with_semaphore(class_name: str, class_url: str):
            async with semaphore:
                return await self.scrape_class(class_name, class_url)

        # Scrape all classes with progress bar
        console.print(f"[cyan]Scraping {len(class_list)} classes...[/cyan]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Scraping classes...", total=len(class_list))

            tasks = [scrape_with_semaphore(name, url) for name, url in class_list]

            classes = []
            for coro in asyncio.as_completed(tasks):
                result = await coro
                if result:
                    classes.append(result)
                progress.update(task, advance=1)

        console.print(f"[green]Successfully scraped {len(classes)} classes[/green]")
        return classes


async def main():
    """Main function for testing scraper"""
    async with OpenStudioDocsScraper(max_concurrent=50) as scraper:
        classes = await scraper.scrape_all_classes()

        # Print summary
        console.print("\n[bold cyan]Scraping Summary[/bold cyan]")
        console.print(f"Total classes: {len(classes)}")
        console.print(f"Total methods: {sum(len(c.methods) for c in classes)}")

        # Print sample class
        if classes:
            sample = classes[0]
            console.print(f"\n[bold]Sample Class:[/bold] {sample.full_name}")
            console.print(f"Description: {sample.description[:100]}...")
            console.print(f"Methods: {len(sample.methods)}")


if __name__ == "__main__":
    asyncio.run(main())
