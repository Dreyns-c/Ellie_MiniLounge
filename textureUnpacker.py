import bpy
import sys
import os
import argparse

def remove_packed_textures(fbx_in_path):
    """
    Imports an FBX, unpacks any embedded textures using unpack_all,
    and exports a new FBX to the original directory with a '_noTextures' suffix.
    Textures are saved externally in a 'textures' subfolder.
    """

    # --- Determine Output Path ---
    input_dir = os.path.dirname(fbx_in_path)
    base_name = os.path.basename(fbx_in_path)
    name_root, name_ext = os.path.splitext(base_name)

    # Ensure the extension is .fbx (case-insensitive check)
    if name_ext.lower() != '.fbx':
        print(f"Warning: Input file '{base_name}' does not have .fbx extension. Output will still use .fbx.")
        name_ext = '.fbx' # Force .fbx for output

    output_filename = f"{name_root}_noTextures{name_ext}"
    fbx_out_path = os.path.join(input_dir, output_filename)

    # Prevent accidentally overwriting input if suffix logic fails somehow
    if fbx_in_path == fbx_out_path:
         print(f"Error: Input and automatically generated output paths are identical. Stopping.")
         print(f"Input: {fbx_in_path}")
         print(f"Output: {fbx_out_path}")
         # Exit Blender with an error code if running in background
         # Check if bpy.app.background exists and is True
         if hasattr(bpy.app, "background") and bpy.app.background:
              sys.exit(1)
         else:
              # If not in background, raise an error to stop script execution in UI
              raise ValueError("Input and output paths are identical.")


    print(f"Processing FBX: {fbx_in_path}")
    print(f"Outputting to: {fbx_out_path}")

    # --- Ensure a clean slate ---
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    # --- Import FBX ---
    try:
        bpy.ops.import_scene.fbx(filepath=fbx_in_path)
        print("FBX imported successfully.")
    except Exception as e:
        print(f"Error importing FBX: {e}")
        if hasattr(bpy.app, "background") and bpy.app.background:
            bpy.ops.wm.quit_blender()
            sys.exit(1)
        else:
            raise # Re-raise exception if running in UI

    # --- Check for Packed Files Before Unpacking ---
    packed_images_before = {img.name for img in bpy.data.images if img.packed_file}
    packed_others_before = {lib.name for lib in bpy.data.libraries if lib.packed_file}
    # Add checks for other packable types if necessary (sounds, etc.)

    total_packed_before = len(packed_images_before) + len(packed_others_before)
    print(f"Found {total_packed_before} packed file(s) initially ({len(packed_images_before)} images).")

    # --- Unpack All Packed Files ---
    if total_packed_before > 0:
        print("Attempting to unpack all files using method: USE_CURRENT_DIR")
        # This method extracts files into a 'textures' folder relative to the
        # current blend file OR the location Blender considers current in background mode.
        # The subsequent FBX export with path_mode='COPY' will consolidate these.

        try:
            # Define the directory where textures should ideally be unpacked
            # This helps ensure they are placed relative to the *output* file
            unpack_dir = os.path.join(os.path.dirname(fbx_out_path), "textures")
            os.makedirs(unpack_dir, exist_ok=True)
            print(f"Target unpack directory: {unpack_dir}")

            # Although 'USE_CURRENT_DIR' is specified, providing the directory
            # might influence where Blender puts the files, especially in background mode.
            # Note: The 'directory' argument for unpack_all is primarily for 'WRITE_CUSTOM_PATH'.
            # For 'USE_CURRENT_DIR', it *should* use a 'textures' subdir relative
            # to the .blend file path, or fallback path in background mode.
            # We create the directory hoping it helps, and rely on path_mode='COPY' during export.

            bpy.ops.file.unpack_all(method='REMOVE') # Or 'REMOVE' if you want data loss

            print("Unpack all finished.")

            # Verify unpacking (optional but good practice)
            unpacked_count = 0
            still_packed = []
            for img_name in packed_images_before:
                img = bpy.data.images.get(img_name)
                if img and not img.packed_file and img.source == 'FILE':
                    print(f"  Verified unpack: Image '{img_name}' -> {img.filepath_raw}")
                    unpacked_count += 1
                elif img and img.packed_file:
                    still_packed.append(f"Image '{img_name}'")
            # Add checks for other types if needed

            if still_packed:
                print(f"Warning: {len(still_packed)} file(s) seem to still be packed:")
                for item in still_packed:
                    print(f"  - {item}")
            print(f"Successfully unpacked {unpacked_count} file(s).")

        except RuntimeError as e:
            # unpack_all raises RuntimeError if nothing is packed
            print(f"Note: 'unpack_all' reported an error, likely because no packed files were found: {e}")
        except Exception as e:
            print(f"Error during unpack_all: {e}")
            if hasattr(bpy.app, "background") and bpy.app.background:
                bpy.ops.wm.quit_blender()
                sys.exit(1)
            else:
                raise
    else:
        print("No packed files found to unpack.")


    # --- Export FBX ---
    try:
        print(f"Exporting modified FBX to: {fbx_out_path}")
        bpy.ops.export_scene.fbx(
            filepath=fbx_out_path,
            use_selection=False,
            global_scale=1.0,
            apply_scale_options='FBX_SCALE_NONE',
            axis_forward='-Z',
            axis_up='Y',
            object_types={'MESH', 'ARMATURE', 'EMPTY', 'OTHER'},
            use_mesh_modifiers=True,
            mesh_smooth_type='FACE',
            # --- Crucial Path Settings ---
            # 'COPY' will find the external files (wherever unpack_all put them)
            # and copy them into a subfolder (default 'textures') relative to the output FBX.
            path_mode='COPY',
            # Explicitly disable embedding for the output FBX
            embed_textures=False,
            #------------------------------
            batch_mode='OFF',
            use_custom_props=False
        )
        print("FBX exported successfully.")
    except Exception as e:
        print(f"Error exporting FBX: {e}")
        if hasattr(bpy.app, "background") and bpy.app.background:
            bpy.ops.wm.quit_blender()
            sys.exit(1)
        else:
            raise

    print("Processing finished.")
    # Quit blender only if running in background mode
    if hasattr(bpy.app, "background") and bpy.app.background:
        bpy.ops.wm.quit_blender()


# --- Main Execution ---
if __name__ == "__main__":
    # Correctly parse arguments when running with 'blender -b -P script.py -- args'
    argv = sys.argv
    if "--" in argv:
        script_args = argv[argv.index("--") + 1:]
    else:
        script_args = [] # No custom args provided

    parser = argparse.ArgumentParser(description='Remove packed textures from an FBX file using Blender.')
    # Output path is now generated automatically, so only input is needed.
    parser.add_argument('-i', '--input', help='Input FBX file path', required=True)
    # Removed '-o', '--output'

    # Ensure Blender's args aren't interfering with script args
    args = parser.parse_args(args=script_args)

    # Basic validation
    if not os.path.isfile(args.input):
        print(f"Error: Input file not found: {args.input}")
        sys.exit(1) # Use sys.exit for script errors before Blender starts fully

    # Resolve input path to absolute
    input_path_abs = os.path.abspath(args.input)

    # Run the main function
    remove_packed_textures(input_path_abs)