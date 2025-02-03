# Ellie_MiniLounge


# The organisation for the 3D assets directories should be as follows :

	/"ASSET_NAME"/

		-/3Dwork/     #3D work related files (.blend, .ma, .sbs... etc)
		-/2Dwork/     #2D work related files where you edit your textures or such (.kra, .psd, .gmp... etc)
		-/Cam/        #if you need to save a 3D camera		
		-/Textures/   #this is where the finished texture files go
		-/Abc/        #this is where you export finished 3d files like .fbx 
		-/Render      #this is where all the render images go
			-/Playblast #for animation playblast (short low res viewport animation)
			-/Preview   #for low quality render images
			-/Batch     #for sequence image rendering
		-/Unity       #root folder for the Unity project
		-/Cache       #this is where you save FX simulation files if needed



# File tree are organised with the root folder in full caps and subsequent files with their first letter capitaled, other files are in lower case.
# To avoid any issues you should avoid using any special character other than "_" and "-" not even space, some software can break if those character
# are present, so to facilitate a problem-less workflow please keep that in mind.
