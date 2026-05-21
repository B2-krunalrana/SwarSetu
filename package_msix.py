import os
import sys
import subprocess
import shutil
import glob
from PIL import Image, ImageDraw, ImageFont

def draw_mic_icon(draw, cx, cy, scale):
    """Draws a premium vector-style microphone icon using PIL drawing tools."""
    hw = int(scale * 0.4)   # Microphone head half-width
    hh = int(scale * 0.9)   # Microphone head height
    
    # 1. Draw microphone body (rounded rectangle in the center)
    # PIL rounded_rectangle is available in newer versions of Pillow
    try:
        draw.rounded_rectangle(
            [cx - hw, cy - hh // 2, cx + hw, cy + hh // 2],
            radius=hw,
            fill=(248, 250, 252)  # White body
        )
    except AttributeError:
        # Fallback to simple rectangle if rounded_rectangle is not supported in active PIL version
        draw.rectangle([cx - hw, cy - hh // 2, cx + hw, cy + hh // 2], fill=(248, 250, 252))
        
    # 2. Draw microphone grill lines
    for y in range(cy - hh // 3, cy + hh // 3, max(2, hh // 6)):
        draw.line([cx - hw + 2, y, cx + hw - 2, y], fill=(9, 13, 22), width=1)
        
    # 3. Draw microphone stand / outer bracket (U-shape)
    bracket_radius = hw + int(scale * 0.15)
    draw.arc(
        [cx - bracket_radius, cy - hh // 4, cx + bracket_radius, cy + hh // 2 + 4],
        start=0,
        end=180,
        fill=(6, 182, 212),  # Cyber Cyan
        width=max(2, int(scale * 0.08))
    )
    
    # 4. Draw vertical stand line
    stand_top = cy + hh // 2 + 4
    stand_bottom = cy + hh // 2 + int(scale * 0.3)
    draw.line(
        [cx, stand_top, cx, stand_bottom],
        fill=(6, 182, 212),
        width=max(2, int(scale * 0.08))
    )
    
    # 5. Draw horizontal stand base
    base_w = hw + int(scale * 0.1)
    draw.line(
        [cx - base_w, stand_bottom, cx + base_w, stand_bottom],
        fill=(6, 182, 212),
        width=max(2, int(scale * 0.08))
    )

def generate_logo_asset(path, size, has_text=False, is_splash=False):
    """Generates a high-quality branding image in the specified size."""
    bg_color = (9, 13, 22)      # #090d16
    cyan_color = (6, 182, 212)  # #06b6d4
    
    img = Image.new("RGBA", size, color=bg_color)
    draw = ImageDraw.Draw(img)
    
    w, h = size
    cx, cy = w // 2, h // 2
    
    # Scale icon based on smallest side
    icon_scale = min(w, h) // 3
    if is_splash:
        icon_scale = h // 4
        
    # Draw icon centered
    icon_cy = cy - 20 if has_text else cy
    draw_mic_icon(draw, cx, icon_cy, icon_scale)
    
    # Draw branding text under the icon
    if has_text:
        try:
            # Try to load standard default font
            font = ImageFont.load_default()
            draw.text((cx, cy + icon_scale // 2 + 10), "SwarSetu", fill=(248, 250, 252), anchor="ms")
            draw.text((cx, cy + icon_scale // 2 + 22), "Voice Bridge", fill=(100, 116, 139), anchor="ms")
        except Exception:
            pass
            
    img.save(path, "PNG")
    print(f"Generated asset: {path} ({w}x{h})")

def find_makeappx():
    """Searches common Windows SDK installation paths for makeappx.exe."""
    sdk_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe",
        r"C:\Program Files\Windows Kits\10\bin\*\x64\makeappx.exe",
        r"C:\Program Files (x86)\Windows Kits\10\App Certification Kit\makeappx.exe",
        r"C:\Program Files\Windows Kits\10\App Certification Kit\makeappx.exe",
    ]
    for pattern in sdk_paths:
        matches = glob.glob(pattern)
        if matches:
            # Return the latest version matching
            return matches[-1]
    return None

def main():
    print("==================================================")
    print("        SwarSetu MSIX Package Creator")
    print("==================================================")
    
    root_dir = os.path.dirname(os.path.abspath(__file__))
    dist_exe = os.path.join(root_dir, "dist", "SwarSetu.exe")
    
    # 1. Verify build executable exists
    if not os.path.exists(dist_exe):
        print("[ERROR] SwarSetu.exe not found in dist/ folder. Please run build.py first to compile it.")
        sys.exit(1)
        
    # 2. Setup AppX layout directory structure
    appx_dir = os.path.join(root_dir, "AppX")
    assets_dir = os.path.join(appx_dir, "Assets")
    
    if os.path.exists(appx_dir):
        print("Cleaning old AppX layout...")
        try:
            shutil.rmtree(appx_dir)
        except PermissionError:
            # Fallback if the directory is locked (e.g. in explorer or IDE)
            for root, dirs, files in os.walk(appx_dir, topdown=False):
                for name in files:
                    try:
                        os.remove(os.path.join(root, name))
                    except Exception:
                        pass
                for name in dirs:
                    try:
                        os.rmdir(os.path.join(root, name))
                    except Exception:
                        pass
        
    os.makedirs(assets_dir, exist_ok=True)
    
    # 3. Copy executable into layout
    shutil.copy2(dist_exe, os.path.join(appx_dir, "SwarSetu.exe"))
    print("Copied SwarSetu.exe into AppX layout folder.")
    
    # 4. Generate visual asset suite
    print("\n[Step 1/3] Generating visual assets for MSIX package...")
    generate_logo_asset(os.path.join(assets_dir, "StoreLogo.png"), (50, 50))
    generate_logo_asset(os.path.join(assets_dir, "Square44x44Logo.png"), (44, 44))
    generate_logo_asset(os.path.join(assets_dir, "Square150x150Logo.png"), (150, 150), has_text=True)
    generate_logo_asset(os.path.join(assets_dir, "Wide310x150Logo.png"), (310, 150), has_text=True)
    generate_logo_asset(os.path.join(assets_dir, "SplashScreen.png"), (620, 300), has_text=True, is_splash=True)
    
    # 5. Write AppxManifest.xml
    print("\n[Step 2/3] Creating AppxManifest.xml configuration...")
    manifest_content = """<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap rescap">

  <Identity
    Name="SwarSetu.VoiceBridge"
    Publisher="CN=SwarSetu"
    Version="1.0.0.0"
    ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>SwarSetu Voice Bridge</DisplayName>
    <PublisherDisplayName>SwarSetu</PublisherDisplayName>
    <Logo>Assets\\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Universal" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22000.0" />
  </Dependencies>

  <Resources>
    <Resource Language="en-us"/>
  </Resources>

  <Applications>
    <Application Id="App"
      Executable="SwarSetu.exe"
      EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="SwarSetu Voice Bridge"
        Description="🎙️ SwarSetu: Real-Time Live Voice Announcement Broadcasting System"
        BackgroundColor="#090d16"
        Square150x150Logo="Assets\\Square150x150Logo.png"
        Square44x44Logo="Assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="Assets\\Wide310x150Logo.png" />
        <uap:SplashScreen Image="Assets\\SplashScreen.png" />
      </uap:VisualElements>
    </Application>
  </Applications>

  <Capabilities>
    <!-- Restricted capability runFullTrust allows direct execution of standard Win32 executables -->
    <rescap:Capability Name="runFullTrust" />
    <Capability Name="internetClient" />
    <!-- Device capability microphone declares that the app accesses system audio devices -->
    <DeviceCapability Name="microphone"/>
  </Capabilities>
</Package>
"""
    manifest_path = os.path.join(appx_dir, "AppxManifest.xml")
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.write(manifest_content)
    print("Created AppxManifest.xml inside AppX layout.")
    
    # 6. Locate makeappx.exe and pack
    print("\n[Step 3/3] Compiling AppX folder into MSIX file...")
    makeappx_exe = find_makeappx()
    
    if makeappx_exe:
        print(f"Found Windows SDK compiler at: {makeappx_exe}")
        output_msix = os.path.join(root_dir, "dist", "SwarSetu.msix")
        
        # Run makeappx pack /d <dir> /p <file> /o
        cmd = [makeappx_exe, "pack", "/d", appx_dir, "/p", output_msix, "/o"]
        print(f"Running command: {' '.join(cmd)}")
        res = subprocess.run(cmd)
        
        if res.returncode == 0:
            print("\n==================================================")
            print("[SUCCESS] MSIX Package compiled successfully!")
            print(f"Path: {output_msix}")
            print("\nMicrosoft Store publishing details:")
            print("1. You can upload this SwarSetu.msix directly to Partner Center.")
            print("2. You DO NOT need to sign the package yourself when uploading to the Microsoft Store;")
            print("   Microsoft signs it with the Store certificate automatically upon release.")
            print("==================================================")
        else:
            print("\n[ERROR] makeappx.exe compilation failed.")
            sys.exit(1)
    else:
        print("\n==================================================")
        print("[NOTICE] Windows SDK 'makeappx.exe' was not found on this system PATH.")
        print(f"However, the complete packaging directory is ready at:\n  {appx_dir}")
        print("\nYou can publish this to the Microsoft Store in two ways:")
        print("Option A (Recommended - Point-and-Click):")
        print("  1. Download the free 'MSIX Packaging Tool' from the Microsoft Store.")
        print("  2. Open it, select 'Create new package' -> 'Package editor'.")
        print("  3. Point it to the AppX directory:")
        print(f"     {appx_dir}")
        print("  4. Click 'Save' to package it into SwarSetu.msix.")
        print("\nOption B (Command Line):")
        print("  Install the Windows SDK (adds makeappx.exe) and run:")
        print(f"  makeappx pack /d {appx_dir} /p dist/SwarSetu.msix /o")
        print("==================================================")

if __name__ == "__main__":
    main()
