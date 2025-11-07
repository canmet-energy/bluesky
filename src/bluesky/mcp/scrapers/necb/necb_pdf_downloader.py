"""
NECB PDF Downloader

Downloads NECB (National Energy Code of Canada for Buildings) PDFs from NRC.
"""

import asyncio
from pathlib import Path
from typing import Dict

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, DownloadColumn, TransferSpeedColumn

console = Console()

# NECB PDF URLs from NRC Publications Archive
NECB_URLS = {
    "2020": {
        "url": "https://nrc-publications.canada.ca/eng/view/ft/?id=af36747e-3eee-4024-a1b4-73833555c7fa&dp=2&dsl=en",
        "filename": "NECB-2020.pdf",
        "size_mb": 3.0,
    },
    "2017": {
        "url": "https://nrc-publications.canada.ca/eng/view/ft/?id=d02dca32-df07-4962-b6e7-0f01dd63cea6&dsl=en",
        "filename": "NECB-2017.pdf",
        "size_mb": 3.5,  # Estimated
    },
    "2015": {
        "url": "https://nrc-publications.canada.ca/eng/view/ft/?id=4f993457-ddd9-4efa-bde9-373b8f7b7a38&dsl=en",
        "filename": "NECB-2015.pdf",
        "size_mb": 3.5,  # Estimated
    },
    "2011": {
        "url": "https://nrc-publications.canada.ca/eng/view/ft/?id=a34734e9-6f66-404f-883c-2361a5a08549&dsl=en",
        "filename": "NECB-2011.pdf",
        "size_mb": 3.5,  # Estimated
    },
}


async def download_necb_pdf(vintage: str, output_dir: Path) -> Path:
    """
    Download a NECB PDF for a specific vintage

    Args:
        vintage: NECB vintage ("2020", "2017", "2015")
        output_dir: Directory to save PDFs

    Returns:
        Path to downloaded PDF file
    """
    if vintage not in NECB_URLS:
        raise ValueError(f"Invalid vintage: {vintage}. Choose from {list(NECB_URLS.keys())}")

    info = NECB_URLS[vintage]
    output_path = output_dir / info["filename"]

    # Skip if already downloaded
    if output_path.exists():
        console.print(f"[green]Already downloaded: {output_path}[/green]")
        return output_path

    console.print(f"[cyan]Downloading NECB {vintage} ({info['size_mb']} MB)...[/cyan]")

    async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(f"NECB {vintage}", total=int(info["size_mb"] * 1024 * 1024))

            async with client.stream("GET", info["url"]) as response:
                response.raise_for_status()

                with open(output_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        progress.update(task, advance=len(chunk))

    console.print(f"[green]Downloaded: {output_path}[/green]")
    return output_path


async def download_all_necb_pdfs(output_dir: Path) -> Dict[str, Path]:
    """
    Download all NECB PDFs

    Args:
        output_dir: Directory to save PDFs

    Returns:
        Dictionary mapping vintage to PDF path
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}
    for vintage in NECB_URLS.keys():
        try:
            pdf_path = await download_necb_pdf(vintage, output_dir)
            results[vintage] = pdf_path
        except Exception as e:
            console.print(f"[red]Error downloading NECB {vintage}: {e}[/red]")

    return results


async def main():
    """Download all NECB PDFs"""
    output_dir = Path(__file__).parent / "pdfs"
    console.print(f"[bold cyan]Downloading NECB PDFs to: {output_dir}[/bold cyan]")

    results = await download_all_necb_pdfs(output_dir)

    console.print("\n[bold green]Download Summary:[/bold green]")
    for vintage, path in results.items():
        size_mb = path.stat().st_size / (1024 * 1024)
        console.print(f"  NECB {vintage}: {path} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
