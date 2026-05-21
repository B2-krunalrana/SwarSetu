import sys
import subprocess
import os
import shutil

def main():
    print("==================================================")
    print("        SwarSetu Desktop App Builder")
    print("==================================================")
    
    # Root directory of the project
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Build React Frontend
    print("\n[Step 1/3] Compiling React Frontend Assets...")
    frontend_dir = os.path.join(root_dir, "frontend")
    if not os.path.exists(frontend_dir):
        print(f"Error: Frontend directory not found at: {frontend_dir}")
        sys.exit(1)
        
    print("Running 'npm run build' inside frontend directory...")
    # On Windows shell=True is required to execute npm.cmd wrapper
    res = subprocess.run("npm run build", shell=True, cwd=frontend_dir)
    if res.returncode != 0:
        print("Error: React compilation failed. Please verify NodeJS / npm is installed and working.")
        sys.exit(1)
    
    dist_dir = os.path.join(frontend_dir, "dist")
    if not os.path.exists(dist_dir) or not os.listdir(dist_dir):
        print(f"Error: React production folder 'frontend/dist' is empty or does not exist.")
        sys.exit(1)
        
    print("[SUCCESS] React frontend compiled successfully in frontend/dist.")
    
    # 2. Determine OS-specific separator for PyInstaller --add-data
    print("\n[Step 2/3] Configuring PyInstaller packaging...")
    
    # PyInstaller syntax for data file bundling:
    # Windows: source;destination
    # Linux/Mac: source:destination
    path_sep = ";" if sys.platform == "win32" else ":"
    
    # Bundle the compiled frontend production files
    add_data_arg = f"frontend/dist{path_sep}frontend/dist"
    
    # Execute PyInstaller using the current Python environment
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",                     # Clean PyInstaller cache before building
        "-y",                          # Overwrite output directory without asking
        "--onefile",                   # Package into a single executable
        "--windowed",                  # Run as a windowed application without a console window
        "--name", "SwarSetu",          # Output executable name
        "--add-data", add_data_arg,    # Bundle React dist assets
        "desktop_app.py"               # Desktop entrypoint script
    ]
    
    # 3. Run PyInstaller
    print("\n[Step 3/3] Executing PyInstaller compiler...")
    print(f"Running command: {' '.join(pyinstaller_cmd)}")
    
    res = subprocess.run(pyinstaller_cmd)
    
    if res.returncode == 0:
        ext = ".exe" if sys.platform == "win32" else ""
        binary_path = os.path.abspath(os.path.join(root_dir, "dist", f"SwarSetu{ext}"))
        print("\n==================================================")
        print("\n[SUCCESS] SwarSetu Standalone Executable Created!")
        print(f"Path: {binary_path}")
        print("Double-click this executable to run the entire app.")
        print("==================================================")
    else:
        print("\n[ERROR] PyInstaller failed to package the application.")
        sys.exit(1)

if __name__ == "__main__":
    main()
