import exiftool, sys, shutil, os
from argparse import ArgumentParser
#exiftool: http://github.com/smarnach/pyexiftool

parser = ArgumentParser()
parser.add_argument('-i', action='store', dest='input', help='Folder with pictures you want to process a.k.a. input folder', required=True)
parser.add_argument('-test', action='store_true', dest='test', help='Test mode')
parsed = parser.parse_args()

supported_exts = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".mov", ".mp4", ".gif", ".bmp", ".m4v"]

in_dir = os.path.abspath(parsed.input)
test_mode = parsed.test

print("Folder:", in_dir)
if test_mode:
	print("*** Test mode enabled. Files will not be renamed! ***")

if not os.path.isdir(in_dir):
	print("Error! This doesn't seem to be a folder:", in_dir)
	sys.exit(1)

def get_extension(fp):
	with exiftool.ExifTool() as et:
		metadata = et.get_metadata(fp)	
	return "." + metadata['File:FileTypeExtension']

wrong_exts = 0
for dirpath, dirnames, filenames in os.walk(in_dir):
	for f in filenames: 
		base, ext = os.path.splitext(f) # original file

		if ext.lower() not in supported_exts:
			continue

		orig_path = os.path.abspath(os.path.join(dirpath,f))

		exiftool_extension = get_extension(orig_path)

		if exiftool_extension.lower() != ext.lower():
			print(orig_path, "should be", exiftool_extension)
			wrong_exts += 1

			if not test_mode:
				new_name = base + exiftool_extension
				new_path = os.path.abspath(os.path.join(dirpath, new_name))

				i = 97 # a
				while os.path.isfile(new_path):
					new_name = base + chr(i) + exiftool_extension
					new_path = os.path.abspath(os.path.join(dirpath, new_name))
					i+=1

				print("Renaming:", orig_path, "-->", new_path)
				shutil.move(orig_path, new_path)
				
if not test_mode:
	print(wrong_exts, "files renamed")
else:
	print(wrong_exts, "files have wrong extensions")
print("Done!")