# --- START OF FILE textureUnpacker.py ---

import bpy
import sys
import os
import argparse
import shutil # Needed for moving files

def unpack_fbx_textures(fbx_in_path):
    """
    Imports an FBX, unpacks any embedded textures using unpack_all(method='USE_LOCAL'),
    then moves the unpacked textures from the temporary 'textures' subdirectory
    into the same directory as the input FBX.
    Does NOT re-export the FBX.
    """

    # --- Determine Input Directory ---
    input_dir = os.path.dirname(fbx_in_path)
    base_name = os.path.basename(fbx_in_path)

    # Check if input exists (redundant with main block but good practice within function)
    if not os.path.isfile(fbx_in_path):
        print(f"Error: Input FBX file not found inside function: {fbx_in_path}")
        if hasattr(bpy.app, "background") and bpy.app.background:
            sys.exit(1)
        else:
            raise FileNotFoundError(f"Input FBX file not found: {fbx_in_path}")

    print(f"Processing FBX: {fbx_in_path}")
    print(f"Target directory for unpacked textures: {input_dir}")

    # --- Ensure a clean slate ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    # Use more robust purging
    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge()
    bpy.ops.outliner.orphans_purge() # Multiple times can help sometimes

    # --- Import FBX ---
    try:
        # Import with image search enabled, might help Blender locate files later if needed
        bpy.ops.import_scene.fbx(filepath=fbx_in_path, use_image_search=True)
        print("FBX imported successfully.")
    except Exception as e:
        print(f"Error importing FBX: {e}")
        if hasattr(bpy.app, "background") and bpy.app.background:
            sys.exit(1)
        else:
            raise # Re-raise exception if running in UI

    # --- Check for Packed Files Before Unpacking ---
    # Store names and original filenames (if available) for later reference
    packed_images_info = {}
    for img in bpy.data.images:
        if img.packed_file:
            # Try to guess original extension if possible, default to png
            original_filename = img.name
            if '.' in img.name: # Simple check if name already contains an extension
                 pass # Keep original name
            else:
                 # Check image format if available, otherwise default
                 # Note: file_format might not be reliable for packed files *before* unpack
                 # We will rely on the filename Blender creates during unpack later
                 original_filename += ".png" # Default assumption

            packed_images_info[img.name] = original_filename

    total_packed_before = len(packed_images_info)
    print(f"Found {total_packed_before} packed image(s) initially.")

    # --- Unpack All Packed Files using USE_LOCAL ---
    unpack_location = None # Track where 'textures' subdir is created
    if total_packed_before > 0:
        print("Attempting to unpack all files using method: USE_LOCAL")
        # This method extracts files into a 'textures' folder relative to the
        # current blend file OR a temporary/working directory in background mode.

        try:
            # This unpacks files and updates the image filepaths internally
            bpy.ops.file.unpack_all(method='USE_LOCAL')
            print("Initial unpack finished.")

        except RuntimeError as e:
            # unpack_all raises RuntimeError if nothing is packed
            # This check should ideally prevent this, but handle just in case
            print(f"Note: 'unpack_all' reported an error, likely because no packed files were found or another issue: {e}")
            # If it failed because nothing was packed, we can just continue
            if "Nothing packed" in str(e):
                 total_packed_before = 0 # Correct the count
            else:
                 raise # Re-raise other runtime errors
        except Exception as e:
            print(f"Error during unpack_all: {e}")
            if hasattr(bpy.app, "background") and bpy.app.background:
                sys.exit(1)
            else:
                raise
    else:
        print("No packed images found to unpack.")

    # --- Move Unpacked Files and Update Paths ---
    moved_count = 0
    failed_to_move = []
    still_packed_after = []
    processed_packed_names = set() # Keep track of images we have dealt with

    if total_packed_before > 0:
        print(f"Scanning images post-unpack to move files to: {input_dir}")
        possible_texture_dirs = set() # Collect potential 'textures' dirs created

        for img in bpy.data.images:
            # Check if this image *was* packed
            if img.name in packed_images_info:
                processed_packed_names.add(img.name)
                # Check if it's *now* unpacked and has a file source
                if not img.packed_file and img.source == 'FILE' and img.filepath:
                    try:
                        # Get the absolute path where Blender unpacked the file
                        # This path will likely be inside a 'textures' subdirectory
                        unpacked_abs_path = bpy.path.abspath(img.filepath_raw)
                        unpacked_dir = os.path.dirname(unpacked_abs_path)
                        unpacked_filename = os.path.basename(unpacked_abs_path)

                        # Record the directory where it was unpacked
                        if os.path.basename(unpacked_dir).lower() == 'textures':
                            possible_texture_dirs.add(unpacked_dir)

                        # Does the unpacked file actually exist?
                        if not os.path.exists(unpacked_abs_path):
                             print(f"  Warning: Image '{img.name}' unpacked according to Blender, but file not found at: {unpacked_abs_path}")
                             failed_to_move.append(f"{img.name} (source file missing)")
                             continue

                        # Construct the desired target path in the input FBX directory
                        target_path = os.path.join(input_dir, unpacked_filename)

                        # Check for conflicts before moving
                        if os.path.exists(target_path):
                            # Simple conflict resolution: skip if identical, warn otherwise
                            if os.path.samefile(unpacked_abs_path, target_path):
                                print(f"  Info: Image '{img.name}' already exists at target location (skipping move): {target_path}")
                                # Update Blender's path just in case it was relative before
                                img.filepath = target_path
                                img.reload() # Good practice after changing source
                                moved_count += 1 # Count it as 'handled'
                                continue
                            else:
                                print(f"  Warning: Image '{img.name}' - Target file already exists and is different. Skipping move: {target_path}")
                                failed_to_move.append(f"{img.name} (target exists: {unpacked_filename})")
                                # Leave Blender pointing to the temp unpacked file for now
                                continue

                        # Move the file
                        print(f"  Moving: '{unpacked_abs_path}' -> '{target_path}'")
                        shutil.move(unpacked_abs_path, target_path)

                        # Update the image path in Blender to the new location
                        img.filepath = target_path # Use absolute path since no .blend is saved
                        img.reload() # Reload image data from new path
                        moved_count += 1

                    except Exception as e:
                        print(f"  Error processing/moving image '{img.name}': {e}")
                        failed_to_move.append(f"{img.name} (error: {e})")

                elif img.packed_file:
                    # If it's still packed, note it down
                    print(f"  Warning: Image '{img.name}' seems to still be packed after unpack attempt.")
                    still_packed_after.append(img.name)
                else:
                     # Was packed, now not packed, but source is not FILE or no filepath?
                     print(f"  Warning: Image '{img.name}' is no longer packed but has unexpected state (source={img.source}, filepath='{img.filepath}').")


            # End of loop for single image

        # Check for any originally packed images that weren't found in the loop
        original_packed_names = set(packed_images_info.keys())
        missing_after_unpack = original_packed_names - processed_packed_names
        if missing_after_unpack:
             print(f"Warning: {len(missing_after_unpack)} image(s) that were initially packed are no longer found in bpy.data.images:")
             for name in missing_after_unpack:
                  print(f"  - {name}")


        print(f"Finished moving files. Moved: {moved_count}, Failed/Skipped: {len(failed_to_move)}, Still Packed: {len(still_packed_after)}")
        if failed_to_move:
            print("  Failures/Skipped Files:")
            for item in failed_to_move:
                print(f"    - {item}")
        if still_packed_after:
             print("  Files Still Packed:")
             for item in still_packed_after:
                  print(f"    - {item}")

        # --- Clean up empty 'textures' directory ---
        # Try removing the 'textures' directory(ies) created by USE_LOCAL if they are empty
        for tex_dir in possible_texture_dirs:
             try:
                  if os.path.exists(tex_dir) and not os.listdir(tex_dir): # Check if empty
                       print(f"  Attempting to remove empty unpack directory: {tex_dir}")
                       os.rmdir(tex_dir)
                  elif os.path.exists(tex_dir):
                       print(f"  Note: Unpack directory is not empty (likely due to failed moves), not removing: {tex_dir}")
             except Exception as e:
                  print(f"  Warning: Could not remove unpack directory '{tex_dir}': {e}")

    # --- No FBX Export ---

    print("\nTexture unpacking process finished.")
    if moved_count > 0 or not failed_to_move:
        print(f"Successfully processed {moved_count} texture(s). Check '{input_dir}' for unpacked files.")
    else:
        print("No textures were successfully unpacked and moved.")


    # Quit blender only if running in background mode
    if hasattr(bpy.app, "background") and bpy.app.background:
        print("Exiting Blender (background mode).")
        bpy.ops.wm.quit_blender()
    else:
        print("\nScript finished. Please check the console for details.")
        # In UI mode, the changes are in memory. User needs to save manually if desired.


# --- Main Execution ---
if __name__ == "__main__":
    # Correctly parse arguments when running with 'blender -b -P script.py -- args'
    argv = sys.argv
    if "--" in argv:
        # Get arguments after '--'
        script_args = argv[argv.index("--") + 1:]
    else:
        # Try getting arguments directly if not run with '--' (e.g., running from Blender Text Editor)
        try:
            script_py_index = -1
            for i, arg in enumerate(argv):
                # Handle potential variations like "blender.exe", "/path/to/blender"
                if arg.endswith(".py") and os.path.basename(arg).lower() == os.path.basename(__file__).lower() :
                    script_py_index = i
                    break
            if script_py_index != -1 and script_py_index + 1 < len(argv):
                 script_args = argv[script_py_index + 1:]
            else:
                 script_args = []
        except Exception:
             script_args = [] # Fallback

    parser = argparse.ArgumentParser(
        description='Unpack embedded textures from an FBX file into its original directory using Blender.'
    )
    parser.add_argument(
        '-i', '--input',
        help='Input FBX file path',
        required=True # Make input mandatory
    )

    # Check if we have any args to parse (especially for UI mode)
    # If running in background, argparse will handle the --input requirement.
    # If in UI and no args are passed via '--', this might show the help message or error out.
    if not script_args and not (hasattr(bpy.app, "background") and bpy.app.background):
         print("Info: Running in UI mode without '--' arguments. Ensure arguments are provided if needed, or script may fail.")
         # Let argparse handle the error if --input is missing

    try:
        args = parser.parse_args(args=script_args)
    except SystemExit as e:
         # argparse throws SystemExit on error (e.g., missing required args, -h)
         print(f"Argument parsing failed with exit code: {e.code}. Check arguments.")
         # If in background mode, exit Blender cleanly
         if hasattr(bpy.app, "background") and bpy.app.background:
              print("Exiting Blender due to argument error.")
              # sys.exit() is cleaner here than bpy.ops.wm.quit_blender() potentially
              sys.exit(e.code if e.code is not None else 1)
         else:
              # In UI mode, just let the script stop, don't exit Blender instance
              # Raising the error makes it visible in the Blender console
               raise # Re-raise the SystemExit to halt script execution

    # --- Input File Validation ---
    input_path_raw = args.input
    # Try to resolve potential relative paths *before* making it absolute
    # This helps if the script is run from a different CWD than the file location
    if not os.path.isabs(input_path_raw):
        # A simple relative path check - might need refinement depending on execution context
        input_path_resolved = os.path.join(os.getcwd(), input_path_raw)
        print(f"Relative input path '{input_path_raw}' resolved to '{input_path_resolved}' based on CWD '{os.getcwd()}'")
    else:
        input_path_resolved = input_path_raw

    input_path_abs = os.path.abspath(input_path_resolved) # Ensure it's absolute and normalized

    if not os.path.isfile(input_path_abs):
        print(f"Error: Input file not found after resolving path: {input_path_abs}")
        print(f"(Original input: '{args.input}')")
        if hasattr(bpy.app, "background") and bpy.app.background:
            sys.exit(1)
        else:
            raise FileNotFoundError(f"Input file not found: {input_path_abs}")

    # Run the main function
    unpack_fbx_textures(input_path_abs)

# --- END OF FILE textureUnpacker.py ---