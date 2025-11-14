#!/bin/bash
set -e

# HOT2000 Setup Script with Pre-packaging Support
# Usage: 
#   ./setup_hot2000.sh                    # Normal setup (uses pre-package if available)
#   ./setup_hot2000.sh --create-package   # Create pre-package for distribution
#   ./setup_hot2000.sh --force-build      # Force build even if pre-package exists

WINE_PREFIX="/home/vscode/.wine_hot2000"
# Always determine script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use environment variable for Docker builds, or script location for normal use
if [ -n "$HOT2000_PACKAGE_DIR" ]; then
    # Docker build environment - use provided package directory
    PACKAGE_DIR="$HOT2000_PACKAGE_DIR"
    PROJECT_ROOT="$(dirname "$PACKAGE_DIR")"  # For Docker context
else
    # Normal environment - use script location to determine project root
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    PACKAGE_DIR="$PROJECT_ROOT/installer"
fi
PACKAGE_FILE="$PACKAGE_DIR/wine_hot2000_prefix.tar.gz"
PACKAGE_METADATA="$PACKAGE_DIR/package_info.json"
CHUNK_SIZE="90M"  # GitHub limit is 100MB, use 90MB for safety

# Parse command line arguments
CREATE_PACKAGE=false
FORCE_BUILD=false
UNINSTALL=false

for arg in "$@"; do
    case $arg in
        --create-package)
            CREATE_PACKAGE=true
            shift
            ;;
        --force-build)
            FORCE_BUILD=true
            shift
            ;;
        --uninstall)
            UNINSTALL=true
            shift
            ;;
        -h|--help)
            echo "HOT2000 Setup Script with Pre-packaging Support"
            echo ""
            echo "Usage:"
            echo "  $0                    # Normal setup (uses pre-package if available)"
            echo "  $0 --create-package   # Create pre-package for distribution"
            echo "  $0 --force-build      # Force build even if pre-package exists"
            echo "  $0 --uninstall        # Completely remove HOT2000 and Wine environment"
            echo ""
            echo "Pre-packaging allows faster, more reliable builds by reusing"
            echo "a complete Wine environment with HOT2000 already installed."
            echo ""
            echo "The --uninstall option removes:"
            echo "  - Wine prefix directory ($WINE_PREFIX)"
            echo "  - hot2000 command wrapper (/usr/local/bin/hot2000)"
            echo "  - HOT2000 log files"
            echo ""
            echo "Pre-package files are preserved for testing package installation."
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

if [ "$UNINSTALL" = true ]; then
    echo "Uninstalling HOT2000 and cleaning Wine environment..."
elif [ "$CREATE_PACKAGE" = true ]; then
    echo "Creating HOT2000 Wine prefix package..."
elif [ "$FORCE_BUILD" = true ]; then
    echo "Force building HOT2000 Wine environment..."
else
    echo "Setting up HOT2000 in Wine environment..."
fi

# Set Wine environment variables
export WINEARCH=win32
export WINEPREFIX="$WINE_PREFIX"
export WINEDEBUG=-all
export DISPLAY=:0

# Function to uninstall HOT2000 and clean environment
uninstall_hot2000() {
    echo "🗑️  Uninstalling HOT2000 and cleaning Wine environment..."
    
    # Ask for confirmation
    echo ""
    echo "This will remove:"
    echo "  - Wine prefix: $WINE_PREFIX"
    echo "  - hot2000 command: /usr/local/bin/hot2000"
    echo "  - HOT2000 log files"
    echo ""
    echo "This will KEEP:"
    echo "  - Pre-package files (for testing package installation)"
    echo ""
    read -p "Are you sure you want to proceed? (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Uninstall cancelled."
        return 0
    fi
    
    echo "Proceeding with uninstall..."
    
    # Stop any running Wine processes
    echo "Stopping Wine processes..."
    pkill -f wine 2>/dev/null || true
    pkill -f wineserver 2>/dev/null || true
    sleep 2
    
    # Kill any remaining Wine processes forcefully
    pkill -9 -f wine 2>/dev/null || true
    pkill -9 -f wineserver 2>/dev/null || true
    
    # Remove Wine prefix directory
    if [ -d "$WINE_PREFIX" ]; then
        echo "Removing Wine prefix: $WINE_PREFIX"
        rm -rf "$WINE_PREFIX"
        echo "✅ Wine prefix removed"
    else
        echo "ℹ️  Wine prefix not found (already clean)"
    fi
    
    # Remove hot2000 wrapper command
    if [ -f "$HOME/.local/bin/hot2000" ]; then
        echo "Removing hot2000 command wrapper..."
        rm -f "$HOME/.local/bin/hot2000"
        echo "✅ hot2000 command removed"
    else
        echo "ℹ️  hot2000 command not found (already clean)"
    fi
    
    # Keep pre-package files for testing
    if [ -f "$PACKAGE_FILE" ]; then
        echo "ℹ️  Keeping pre-package for testing: $PACKAGE_FILE"
    elif [ -f "$PACKAGE_FILE.partaa" ]; then
        local chunk_count=$(ls "$PACKAGE_FILE".part* 2>/dev/null | wc -l)
        echo "ℹ️  Keeping chunked pre-package for testing: $chunk_count chunks"
    fi
    
    if [ -f "$PACKAGE_METADATA" ]; then
        echo "ℹ️  Keeping package metadata for testing: $PACKAGE_METADATA"
    fi
    
    # Clean up any HOT2000 log files in the project
    echo "Cleaning HOT2000 log files..."
    find "$PROJECT_ROOT" -name "*_hot2000.log" -delete 2>/dev/null || true
    
    # Clean up temporary X11 processes if any
    pkill -f "Xvfb :99" 2>/dev/null || true
    
    echo ""
    echo "✅ HOT2000 uninstall completed successfully!"
    echo ""
    echo "Your system is now clean and ready for a fresh installation."
    echo "To reinstall, run: $0 --force-build"
    
    return 0
}

# Function to create package metadata
create_package_metadata() {
    local package_file="$1"
    local metadata_file="$2"
    local chunk_count="${3:-0}"
    
    if [ "$chunk_count" -gt 0 ]; then
        # Chunked file metadata
        local total_size=0
        for chunk in "$package_file".part*; do
            if [ -f "$chunk" ]; then
                chunk_size=$(stat -c%s "$chunk" 2>/dev/null || stat -f%z "$chunk" 2>/dev/null || echo "0")
                total_size=$((total_size + chunk_size))
            fi
        done
        
        cat > "$metadata_file" << EOF
{
    "package_file": "$(basename "$package_file")",
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "wine_arch": "$WINEARCH",
    "wine_prefix": "$WINE_PREFIX",
    "hot2000_path": "drive_c/h2kcli/HOT2000.exe",
    "package_size_bytes": $total_size,
    "chunked": true,
    "chunk_count": $chunk_count,
    "chunk_size": "$CHUNK_SIZE",
    "chunk_pattern": "$(basename "$package_file").part*",
    "creator": "setup_hot2000.sh",
    "wine_version": "$(wine --version 2>/dev/null || echo 'unknown')",
    "system_info": {
        "os": "$(uname -s)",
        "arch": "$(uname -m)",
        "kernel": "$(uname -r)"
    }
}
EOF
    else
        # Single file metadata
        cat > "$metadata_file" << EOF
{
    "package_file": "$(basename "$package_file")",
    "created_date": "$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
    "wine_arch": "$WINEARCH",
    "wine_prefix": "$WINE_PREFIX",
    "hot2000_path": "drive_c/h2kcli/HOT2000.exe",
    "package_size_bytes": $(stat -c%s "$package_file" 2>/dev/null || stat -f%z "$package_file" 2>/dev/null || echo "0"),
    "chunked": false,
    "creator": "setup_hot2000.sh",
    "wine_version": "$(wine --version 2>/dev/null || echo 'unknown')",
    "system_info": {
        "os": "$(uname -s)",
        "arch": "$(uname -m)",
        "kernel": "$(uname -r)"
    }
}
EOF
    fi
}

# Function to get GitHub token from git credential helper (VS Code authentication)
get_github_token_from_git() {
    local token
    token=$(printf "protocol=https\nhost=github.com\n" | git credential fill 2>/dev/null | grep '^password=' | cut -d= -f2)

    if [ -n "$token" ]; then
        echo "$token"
        return 0
    else
        return 1
    fi
}

# Function to download file via GitHub API using token
download_file_with_token() {
    local repo="$1"
    local path="$2"
    local output="$3"
    local token="$4"

    local url="https://api.github.com/repos/$repo/contents/$path"

    if curl -f -s -H "Authorization: token $token" \
        -H "Accept: application/vnd.github.raw" \
        "$url" > "$output" 2>/dev/null; then
        return 0
    else
        return 1
    fi
}

# Function to download pre-package from GitHub
download_prepackage_from_github() {
    local github_repo="canmet-energy/container_h2kcli"
    local github_path="installer"
    local base_filename="wine_hot2000_prefix.tar.gz"
    local use_gh_cli=false
    local github_token=""

    echo "🌐 Attempting to download pre-package from GitHub..."
    echo "Repository: $github_repo"

    # Determine authentication method
    if command -v gh &> /dev/null && gh auth status &> /dev/null; then
        echo "✅ Using GitHub CLI authentication"
        use_gh_cli=true
    else
        # Try git credential helper (VS Code authentication)
        echo "ℹ️  GitHub CLI not available, trying VS Code authentication..."
        github_token=$(get_github_token_from_git)

        if [ -n "$github_token" ]; then
            echo "✅ Using VS Code git credential authentication"
            use_gh_cli=false
        else
            echo "❌ No GitHub authentication found"
            echo "Solutions:"
            echo "  1. Run: gh auth login  (for GitHub CLI)"
            echo "  2. Or authenticate VS Code with GitHub"
            return 1
        fi
    fi

    # Create package directory if it doesn't exist
    mkdir -p "$PACKAGE_DIR"

    # Download metadata file first to determine if chunked
    echo "Downloading package metadata..."
    local metadata_success=false

    if [ "$use_gh_cli" = true ]; then
        if gh api "repos/$github_repo/contents/$github_path/package_info.json" \
            -H "Accept: application/vnd.github.raw" > "$PACKAGE_METADATA" 2>/dev/null; then
            metadata_success=true
        fi
    else
        if download_file_with_token "$github_repo" "$github_path/package_info.json" \
            "$PACKAGE_METADATA" "$github_token"; then
            metadata_success=true
        fi
    fi

    if [ "$metadata_success" = false ]; then
        echo "⚠️  Could not download package metadata (package_info.json not found)"
        echo "Trying to download chunks directly..."

        # Try downloading first chunk to see if chunked files exist
        local first_chunk_success=false

        if [ "$use_gh_cli" = true ]; then
            if gh api "repos/$github_repo/contents/$github_path/${base_filename}.partaa" \
                -H "Accept: application/vnd.github.raw" > "$PACKAGE_FILE.partaa" 2>/dev/null; then
                first_chunk_success=true
            fi
        else
            if download_file_with_token "$github_repo" "$github_path/${base_filename}.partaa" \
                "$PACKAGE_FILE.partaa" "$github_token"; then
                first_chunk_success=true
            fi
        fi

        if [ "$first_chunk_success" = true ]; then
            echo "✅ Found chunked package, downloading remaining chunks..."

            # Download remaining chunks (partab, partac, etc.)
            local suffix
            for suffix in ab ac ad ae af ag ah ai aj ak al am an ao ap aq ar as at au av aw ax ay az \
                          ba bb bc bd be bf bg bh bi bj bk bl bm bn bo bp bq br bs bt bu bv bw bx by bz; do
                local chunk_file="$PACKAGE_FILE.part$suffix"
                local chunk_success=false

                if [ "$use_gh_cli" = true ]; then
                    if gh api "repos/$github_repo/contents/$github_path/${base_filename}.part$suffix" \
                        -H "Accept: application/vnd.github.raw" > "$chunk_file" 2>/dev/null; then
                        chunk_success=true
                    fi
                else
                    if download_file_with_token "$github_repo" "$github_path/${base_filename}.part$suffix" \
                        "$chunk_file" "$github_token"; then
                        chunk_success=true
                    fi
                fi

                if [ "$chunk_success" = true ]; then
                    echo "  Downloaded chunk: part$suffix"
                else
                    # No more chunks
                    break
                fi
            done

            echo "✅ Pre-package chunks downloaded successfully from GitHub"
            return 0
        else
            # Try single file
            echo "No chunked files found, trying single package file..."
            local single_file_success=false

            if [ "$use_gh_cli" = true ]; then
                if gh api "repos/$github_repo/contents/$github_path/$base_filename" \
                    -H "Accept: application/vnd.github.raw" > "$PACKAGE_FILE" 2>/dev/null; then
                    single_file_success=true
                fi
            else
                if download_file_with_token "$github_repo" "$github_path/$base_filename" \
                    "$PACKAGE_FILE" "$github_token"; then
                    single_file_success=true
                fi
            fi

            if [ "$single_file_success" = true ]; then
                echo "✅ Pre-package downloaded successfully from GitHub"
                return 0
            else
                echo "❌ Could not find pre-package on GitHub"
                return 1
            fi
        fi
    fi

    # Parse metadata to determine if chunked
    local is_chunked=$(jq -r '.chunked // false' "$PACKAGE_METADATA" 2>/dev/null || echo "false")

    if [ "$is_chunked" = "true" ]; then
        local chunk_count=$(jq -r '.chunk_count // 0' "$PACKAGE_METADATA" 2>/dev/null || echo "0")
        echo "Package is chunked into $chunk_count parts, downloading..."

        # Download all chunks
        local chunk_num=0
        local suffix
        for suffix in aa ab ac ad ae af ag ah ai aj ak al am an ao ap aq ar as at au av aw ax ay az \
                      ba bb bc bd be bf bg bh bi bj bk bl bm bn bo bp bq br bs bt bu bv bw bx by bz; do
            if [ $chunk_num -ge $chunk_count ]; then
                break
            fi

            echo "  Downloading chunk part$suffix ($((chunk_num + 1))/$chunk_count)..."
            local chunk_dl_success=false

            if [ "$use_gh_cli" = true ]; then
                if gh api "repos/$github_repo/contents/$github_path/${base_filename}.part$suffix" \
                    -H "Accept: application/vnd.github.raw" > "$PACKAGE_FILE.part$suffix" 2>/dev/null; then
                    chunk_dl_success=true
                fi
            else
                if download_file_with_token "$github_repo" "$github_path/${base_filename}.part$suffix" \
                    "$PACKAGE_FILE.part$suffix" "$github_token"; then
                    chunk_dl_success=true
                fi
            fi

            if [ "$chunk_dl_success" = false ]; then
                echo "❌ Failed to download chunk part$suffix"
                return 1
            fi

            chunk_num=$((chunk_num + 1))
        done

        echo "✅ All $chunk_count chunks downloaded successfully"
    else
        # Download single file
        echo "Downloading single package file..."
        local single_dl_success=false

        if [ "$use_gh_cli" = true ]; then
            if gh api "repos/$github_repo/contents/$github_path/$base_filename" \
                -H "Accept: application/vnd.github.raw" > "$PACKAGE_FILE" 2>/dev/null; then
                single_dl_success=true
            fi
        else
            if download_file_with_token "$github_repo" "$github_path/$base_filename" \
                "$PACKAGE_FILE" "$github_token"; then
                single_dl_success=true
            fi
        fi

        if [ "$single_dl_success" = false ]; then
            echo "❌ Failed to download package file"
            return 1
        fi

        echo "✅ Package downloaded successfully"
    fi

    echo "✅ Pre-package downloaded successfully from GitHub"
    return 0
}

# Function to extract and use pre-package
use_prepackage() {
    local package_file="$1"
    local metadata_file="$2"
    
    echo "Using pre-packaged Wine environment..."
    echo "Package: $(basename "$package_file")"
    
    # Check if package is chunked
    local is_chunked=false
    if [ -f "$metadata_file" ]; then
        is_chunked=$(jq -r '.chunked // false' "$metadata_file" 2>/dev/null || echo "false")
        echo "Package created: $(jq -r '.created_date // "unknown"' "$metadata_file" 2>/dev/null || echo "unknown")"
        echo "Package size: $(jq -r '.package_size_bytes // "unknown"' "$metadata_file" 2>/dev/null | numfmt --to=iec 2>/dev/null || echo "unknown")"
        
        if [ "$is_chunked" = "true" ]; then
            local chunk_count=$(jq -r '.chunk_count // 0' "$metadata_file" 2>/dev/null || echo "0")
            echo "Package is chunked into $chunk_count parts"
        fi
    fi
    
    # Remove existing Wine prefix
    rm -rf "$WINE_PREFIX"
    
    # Handle chunked vs single file extraction
    if [ "$is_chunked" = "true" ] && [ -f "$package_file.partaa" ]; then
        echo "Reassembling chunked package..."
        
        # Verify all chunks are present
        local expected_chunks=$(jq -r '.chunk_count // 0' "$metadata_file" 2>/dev/null || echo "0")
        local actual_chunks=$(ls "$package_file".part* 2>/dev/null | wc -l)
        
        if [ "$actual_chunks" -ne "$expected_chunks" ]; then
            echo "ERROR: Expected $expected_chunks chunks, found $actual_chunks"
            return 1
        fi
        
        echo "Found all $actual_chunks chunks, reassembling..."
        
        # Reassemble the chunks
        cat "$package_file".part* > "$package_file.temp"
        
        # Extract the reassembled file
        echo "Extracting Wine prefix..."
        mkdir -p "$(dirname "$WINE_PREFIX")"
        tar -xzf "$package_file.temp" -C "$(dirname "$WINE_PREFIX")"
        
        # Clean up temporary file
        rm "$package_file.temp"
        
    elif [ -f "$package_file" ]; then
        # Single file extraction
        echo "Extracting Wine prefix..."
        mkdir -p "$(dirname "$WINE_PREFIX")"
        tar -xzf "$package_file" -C "$(dirname "$WINE_PREFIX")"
        
    else
        echo "ERROR: Neither single package file nor chunks found"
        echo "Looking for: $package_file or $package_file.partaa"
        return 1
    fi
    
    # Ensure correct ownership
    sudo chown -R vscode:vscode "$WINE_PREFIX" 2>/dev/null || true
    
    echo "Pre-package extraction completed successfully!"
    return 0
}

# Function to create pre-package
create_prepackage() {
    local package_file="$1"
    local metadata_file="$2"
    
    echo "Creating pre-package from current Wine environment..."
    
    if [ ! -d "$WINE_PREFIX" ]; then
        echo "ERROR: Wine prefix does not exist at $WINE_PREFIX"
        echo "Run a normal build first to create the Wine environment."
        exit 1
    fi
    
    if [ ! -f "$WINE_PREFIX/drive_c/h2kcli/HOT2000.exe" ]; then
        echo "ERROR: HOT2000.exe not found in Wine prefix"
        echo "Complete a successful HOT2000 installation first."
        exit 1
    fi
    
    # Clean up temporary files in Wine prefix
    echo "Cleaning Wine prefix before packaging..."
    rm -rf "$WINE_PREFIX/drive_c/users/$(whoami)/Temp/"* 2>/dev/null || true
    rm -rf "$WINE_PREFIX/drive_c/windows/Temp/"* 2>/dev/null || true
    find "$WINE_PREFIX" -name "*.log" -delete 2>/dev/null || true
    find "$WINE_PREFIX" -name "*_hot2000.log" -delete 2>/dev/null || true
    
    # Create package directory (should already exist)
    mkdir -p "$PACKAGE_DIR"
    
    # Create the package
    echo "Packaging Wine prefix..."
    cd "$(dirname "$WINE_PREFIX")"
    tar -czf "$package_file" "$(basename "$WINE_PREFIX")"
    
    # Check if file needs to be split for GitHub compatibility
    FILE_SIZE=$(stat -c%s "$package_file" 2>/dev/null || stat -f%z "$package_file" 2>/dev/null)
    FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
    
    if [ $FILE_SIZE_MB -gt 90 ]; then
        echo "Package size ($FILE_SIZE_MB MB) exceeds GitHub limit, splitting into chunks..."
        
        # Split the file
        split -b $CHUNK_SIZE "$package_file" "$package_file.part"
        
        # Remove the original large file
        rm "$package_file"
        
        # List the created chunks
        echo "Created chunks:"
        ls -lh "$package_file".part* | while read -r line; do
            echo "  $line"
        done
        
        # Update metadata to reflect chunked storage
        CHUNK_COUNT=$(ls "$package_file".part* | wc -l)
        echo "Split into $CHUNK_COUNT chunks of max $CHUNK_SIZE each"
        
        # Create metadata with chunk information
        create_package_metadata "$package_file" "$metadata_file" "$CHUNK_COUNT"
    else
        echo "Package size ($FILE_SIZE_MB MB) is within GitHub limits, no splitting needed"
        # Create metadata for single file
        create_package_metadata "$package_file" "$metadata_file"
    fi
    
    echo "✅ Pre-package created successfully!"
    if [ -f "$package_file" ]; then
        echo "Package: $package_file"
        echo "Size: $(du -h "$package_file" | cut -f1)"
    else
        echo "Package: $package_file (chunked)"
        echo "Total size: $(du -ch "$package_file".part* | tail -n1 | cut -f1)"
        echo "Chunks: $(ls "$package_file".part* | wc -l) files"
    fi
    echo "Metadata: $metadata_file"
    
    return 0
}

# Function to perform full Wine installation
perform_full_installation() {
    echo "Performing full Wine installation..."
    
    # Ensure X11 socket directory has correct permissions
    sudo mkdir -p /tmp/.X11-unix
    sudo chmod 1777 /tmp/.X11-unix

    # Ensure proper permissions
    sudo chown -R vscode:vscode "$WINE_PREFIX" 2>/dev/null || true
    sudo chown -R vscode:vscode /opt/hot2000 2>/dev/null || true

    # Initialize Wine with GUI support
    echo "Initializing Wine prefix..."
    wineboot -i

    # Wait for Wine to stabilize
    sleep 3

    # Install Visual C++ Redistributables for better compatibility
    echo "Installing Visual C++ Redistributables..."
    winetricks -q vcrun2019 || echo "vcrun2019 installation completed with warnings"

    # Install HOT2000
    echo "Installing HOT2000..."
    wine /opt/hot2000/installer.exe /DIR="C:\\h2kcli" /VERYSILENT

    # Wait for installation to complete
    sleep 5

    # Verify installation
    if [ -f "$WINE_PREFIX/drive_c/h2kcli/HOT2000.exe" ]; then
        echo "HOT2000 installation successful!"
        return 0
    else
        echo "HOT2000 installation may have failed - executable not found"
        return 1
    fi
}

# Function to create the hot2000 wrapper script
create_hot2000_wrapper() {
    echo "Creating enhanced 'hot2000' command wrapper..."
    
    # Check if the template script exists before trying to modify it
    if [ ! -f "$SCRIPT_DIR/hot2000" ]; then
        echo "Error: hot2000 wrapper script not found at $SCRIPT_DIR/hot2000"
        echo "Available files in $SCRIPT_DIR:"
        ls -la "$SCRIPT_DIR/" || echo "Failed to list directory contents"
        return 0
    fi
    
    # Ensure the template script is executable
    chmod +x "$SCRIPT_DIR/hot2000"

    # Ensure ~/.local/bin directory exists
    mkdir -p "$HOME/.local/bin"

    # Remove any existing symbolic link
    rm -f "$HOME/.local/bin/hot2000"

    # Create symbolic link to the template script
    ln -sf "$SCRIPT_DIR/hot2000" "$HOME/.local/bin/hot2000"

    echo "Created enhanced 'hot2000' command wrapper with timeout and dialog logging"
    echo "Installed to: $HOME/.local/bin/hot2000"
}

# Main execution logic
main() {
    # Handle uninstall mode
    if [ "$UNINSTALL" = true ]; then
        uninstall_hot2000
        exit $?
    fi
    
    # Handle create package mode
    if [ "$CREATE_PACKAGE" = true ]; then
        create_prepackage "$PACKAGE_FILE" "$PACKAGE_METADATA"
        exit $?
    fi
    
    # Check if we should use a pre-package (unless force build is specified)
    # Check for either single file or chunked files
    if [ "$FORCE_BUILD" = false ] && ([ -f "$PACKAGE_FILE" ] || [ -f "$PACKAGE_FILE.partaa" ]); then
        echo "Pre-package found, using it for faster setup..."
        if use_prepackage "$PACKAGE_FILE" "$PACKAGE_METADATA"; then
            create_hot2000_wrapper
            echo "✅ HOT2000 setup complete using pre-package!"
        else
            echo "❌ Failed to use pre-package, falling back to full installation..."
            perform_full_installation
            if [ $? -eq 0 ]; then
                create_hot2000_wrapper
                echo "✅ HOT2000 setup complete via full installation!"
            else
                echo "❌ HOT2000 installation failed"
                exit 1
            fi
        fi
    else
        # No local pre-package found
        if [ "$FORCE_BUILD" = true ]; then
            echo "Force build requested, skipping pre-package check..."
        else
            echo "No local pre-package found, attempting GitHub download..."

            # Try downloading from GitHub
            if download_prepackage_from_github; then
                echo "GitHub download successful, using downloaded pre-package..."
                if use_prepackage "$PACKAGE_FILE" "$PACKAGE_METADATA"; then
                    create_hot2000_wrapper
                    echo "✅ HOT2000 setup complete using GitHub pre-package!"
                    exit 0
                else
                    echo "❌ Failed to use downloaded pre-package, falling back to full installation..."
                fi
            else
                echo "GitHub download failed or unavailable, falling back to full installation..."
            fi
        fi

        # Perform full installation
        echo "Performing full installation from scratch..."

        # Check if we're in Docker build without display capability
        if [ -n "$HOT2000_PACKAGE_DIR" ] && [ -z "$DISPLAY" ] && ! xset q &>/dev/null; then
            echo "❌ Running in Docker build environment without display capability."
            echo "❌ Full Hot2000 installation requires GUI for Wine initialization."
            echo ""
            echo "Solutions:"
            echo "  1. Pre-package available on GitHub will be downloaded automatically"
            echo "  2. Ensure gh CLI is authenticated: gh auth login"
            echo "  3. Or create a pre-package manually in dev environment:"
            echo "     ./scripts/setup_hot2000.sh --create-package"
            echo "  4. Or run this script manually in the running container:"
            echo "     bash /opt/hot2000/setup_hot2000.sh"
            echo ""
            echo "Docker build will complete, but Hot2000 is not installed."
            exit 0  # Don't fail the build, just skip installation
        fi

        perform_full_installation
        if [ $? -eq 0 ]; then
            create_hot2000_wrapper
            echo "✅ HOT2000 setup complete!"

            # Offer to create pre-package
            echo ""
            echo "💡 Tip: You can create a pre-package for faster future builds:"
            echo "   $0 --create-package"
        else
            echo "❌ HOT2000 installation failed"
            exit 1
        fi
    fi
    
    # Display usage information
    echo ""
    echo "Usage:"
    echo "  # Work with copies to preserve originals"
    echo "  cp examples/3Storey_8Unit.h2k my_analysis.h2k"
    echo "  hot2000 my_analysis.h2k"
    echo ""
    echo "  # Direct usage (modifies input file)"
    echo "  hot2000 $PROJECT_ROOT/examples/3Storey_8Unit.h2k"
    echo ""
    echo "Pre-package management:"
    echo "  $0 --create-package   # Create pre-package from current installation"
    echo "  $0 --force-build      # Force full build (ignore pre-package)"
    echo "  $0 --uninstall        # Completely remove HOT2000 and clean environment"
    echo ""
    echo "Pre-packages are stored in: $PROJECT_ROOT/installer/"
}

# Run main function
main "$@"