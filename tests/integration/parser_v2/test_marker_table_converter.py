"""Test Marker TableConverter with Ollama LLM enhancement

This test uses the CORRECT Marker API:
- TableConverter (not PdfConverter)
- Ollama LLM service for enhanced accuracy
- JSON output format
"""

from pathlib import Path
from marker.converters.table import TableConverter
from marker.models import create_model_dict
from marker.renderers.json import JSONRenderer

# NECB PDF path
NECB_2020_PATH = Path("/workspaces/bluesky/src/bluesky/mcp/scrapers/necb/pdfs/NECB-2020.pdf")

def test_marker_with_llm():
    """
    Test Marker TableConverter with Ollama LLM on NECB 2020

    Configuration:
    - TableConverter: Specialized for table extraction
    - use_llm=True: Enable LLM enhancement (llama3.2-vision)
    - output_format=json: Get structured cell-level data
    """
    print("=" * 80)
    print("MARKER TABLE CONVERTER TEST (with LLM Enhancement)")
    print("=" * 80)

    if not NECB_2020_PATH.exists():
        print(f"❌ PDF not found: {NECB_2020_PATH}")
        return

    print(f"\n📄 PDF: {NECB_2020_PATH.name}")
    print(f"   Size: {NECB_2020_PATH.stat().st_size / 1024 / 1024:.1f} MB")

    # Create model dictionary
    print("\n📦 Loading Marker models...")
    models = create_model_dict()

    # Initialize TableConverter with configuration
    print("\n🔧 Initializing TableConverter...")
    print("   LLM service: marker.services.ollama.OllamaService")
    print("   LLM model: llama3.2-vision")

    # Create config with use_llm enabled
    config = {
        "use_llm": True,  # Enable LLM enhancement
        "output_format": "json",  # Get structured output
    }

    # Pass Ollama service path (string) to TableConverter
    converter = TableConverter(
        artifact_dict=models,
        llm_service="marker.services.ollama.OllamaService",  # ✅ Pass string path
        config=config
    )

    # Override renderer to use JSON
    converter.renderer = JSONRenderer

    print("\n⚙️  Configuration:")
    print(f"   use_llm: True")
    print(f"   output_format: json")
    print(f"   LLM service: OllamaService")

    # Setup caching
    cache_dir = Path("/tmp/marker_cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "NECB-2020.tableconverter.pkl"

    print(f"\n💾 Cache configuration:")
    print(f"   Cache file: {cache_file}")
    print(f"   Exists: {cache_file.exists()}")

    try:
        import time
        import pickle

        # Check cache first
        if cache_file.exists():
            print("\n📦 Loading from cache...")
            start_time = time.time()
            with open(cache_file, "rb") as f:
                result = pickle.load(f)
            elapsed = time.time() - start_time
            print(f"✅ Loaded from cache in {elapsed:.1f}s")
        else:
            print("\n🚀 Running Marker extraction...")
            print("   (This will take 60-90 minutes for 315-page PDF)")
            print("   Press Ctrl+C to cancel\n")

            start_time = time.time()

            # Run conversion
            result = converter(str(NECB_2020_PATH))

            elapsed = time.time() - start_time
            print(f"\n✅ Extraction complete in {elapsed / 60:.1f} minutes ({elapsed:.0f}s)")

            # Save to cache
            print(f"\n💾 Saving to cache: {cache_file}")
            with open(cache_file, "wb") as f:
                pickle.dump(result, f)
            print(f"✅ Cache saved ({cache_file.stat().st_size / 1024 / 1024:.1f} MB)")

        # Analyze result
        print("\n" + "=" * 80)
        print("RESULT ANALYSIS")
        print("=" * 80)

        print(f"\nResult type: {type(result)}")

        if hasattr(result, '__dict__'):
            attrs = list(result.__dict__.keys())
            print(f"Attributes: {attrs}")

            # Check for table data
            if hasattr(result, 'pages'):
                print(f"\n📄 Pages: {len(result.pages)}")

                # Find page 73 (0-indexed = 72)
                if len(result.pages) > 72:
                    page_73 = result.pages[72]
                    print(f"\n🎯 Page 73 structure:")
                    print(f"   Blocks: {len(page_73.structure) if hasattr(page_73, 'structure') else 'N/A'}")

                    if hasattr(page_73, 'structure'):
                        tables_on_page = [b for b in page_73.structure if hasattr(b, 'block_type') and 'table' in str(b.block_type).lower()]
                        print(f"   Tables: {len(tables_on_page)}")

                        if tables_on_page:
                            print(f"\n📊 First table on page 73:")
                            table = tables_on_page[0]
                            print(f"   Type: {table.block_type if hasattr(table, 'block_type') else 'Unknown'}")
                            if hasattr(table, 'html'):
                                print(f"   HTML length: {len(table.html)} chars")
                                print(f"   First 200 chars:")
                                print(f"   {table.html[:200]}")

        # Save result for inspection
        output_file = Path("/tmp/marker_table_converter_result.json")
        print(f"\n💾 Saving result to: {output_file}")

        import json
        with open(output_file, "w") as f:
            # Convert result to dict if possible
            if hasattr(result, 'model_dump'):
                json.dump(result.model_dump(), f, indent=2)
            elif hasattr(result, '__dict__'):
                # Manually serialize
                data = {"type": str(type(result)), "attributes": str(result.__dict__)}
                json.dump(data, f, indent=2)
            else:
                json.dump({"result": str(result)}, f, indent=2)

        print(f"✅ Result saved")

    except KeyboardInterrupt:
        print("\n\n⚠️  Extraction cancelled by user")
    except Exception as e:
        print(f"\n\n❌ Extraction failed:")
        print(f"   Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_marker_with_llm()
