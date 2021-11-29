import exiftool, sys, shutil, os, hashlib
from tqdm import tqdm
from argparse import ArgumentParser
#exiftool: http://github.com/smarnach/pyexiftool

# Use this for finding metadata tags
#with exiftool.ExifTool() as et:
#		metadata = et.get_metadata(sys.argv[1])
# 		sys.exit(1)

PICS_ONLY = False
VIDS_ONLY = False

parser = ArgumentParser()
parser.add_argument('-i', action='store', dest='input', help='Folder with photos', required=True)
parser.add_argument('-o', action='store', dest='output', help='Photos will be copied here', required=True)
parser.add_argument('-pics', dest='picsonly', action='store_true')
parser.add_argument('-vids', dest='vidsonly', action='store_true')
parser.set_defaults(picsonly=False, vidsonly=False)
parsed = parser.parse_args()

if parsed.picsonly:
	print("*** PICS ONLY ***")
	PICS_ONLY = True
	VIDS_ONLY = False
elif parsed.vidsonly:
	print("*** VIDS ONLY ***")
	PICS_ONLY = False
	VIDS_ONLY = True

ignored_files = [".DS_Store", "PLEDB", "PLEDB_Hashes.txt"]
ignored_file_exts = [".bat", ".sh", ".py", ".zip", ".7z"]
video_exts = [".mov", ".mp4", ".avi", ".m4v", ".mkv"]

in_dir = os.path.abspath(parsed.input)


# Check if input is a .photoslibrary, if so correct it to point to the originals folder
if ".photoslibrary" in in_dir:
	test_PhotosLibrary_path = os.path.join(in_dir, "originals/")
	if os.path.isdir(test_PhotosLibrary_path):
		in_dir = test_PhotosLibrary_path
	
	test_PhotosLibrary_path = os.path.join(in_dir, "Masters/") # high sierra
	if os.path.isdir(test_PhotosLibrary_path):
		in_dir = test_PhotosLibrary_path

out_dir = os.path.abspath(parsed.output)
already_processed_md5 = os.path.join(out_dir, 'PLEDB_Hashes.txt')

print("Input folder:", in_dir)
print("Destination:", out_dir)
print("---")

if not os.path.isdir(in_dir):
	print("Error! This doesn't seem to be a folder:", in_dir)
	sys.exit(1)

if not os.path.isdir(out_dir):
	print("Making output folder:", out_dir)
	os.makedirs(out_dir)

contentID_filenames = [] # for Live Photos
contentID_IDs = []
handled_md5s = []

def md5sum(filename):
	with open(filename, "rb") as f:
		file_hash = hashlib.blake2b()
		while chunk := f.read(8192):
			file_hash.update(chunk)
	#print(filename, file_hash.hexdigest())
	return file_hash.hexdigest()

def grab_metadata(fp):
	with exiftool.ExifTool() as et:
		metadata = et.get_metadata(fp)	
	#print(metadata)
	
	if 'QuickTime:ContentCreateDate' in metadata: # usually the date to go by for videos transcoded in Photos.app... CreateDate will be the transcode date for those
		date = metadata['QuickTime:ContentCreateDate']
	elif 'EXIF:DateTimeOriginal' in metadata:
		date = metadata['EXIF:DateTimeOriginal']
	elif 'EXIF:CreateDate' in metadata:
		date = metadata['EXIF:CreateDate']
	elif 'QuickTime:CreateDate' in metadata:
		date = metadata['QuickTime:CreateDate']
	elif 'EXIF:ModifyDate' in metadata:
		date = metadata['EXIF:ModifyDate']
	else:
		date = False

	if 'MakerNotes:ContentIdentifier' in metadata:
		content_ID = metadata['MakerNotes:ContentIdentifier']
	elif 'QuickTime:ContentIdentifier' in metadata:
		content_ID = metadata['QuickTime:ContentIdentifier']
	else:
		content_ID = False

	return {"date": date, "content_ID": content_ID }

def destination_from_date(in_date, in_path):
	f = os.path.basename(in_path)
	if in_date:
		date = in_date.split(' ')[0]
		time = in_date.split(' ')[1]

		year = date.split(':')[0]
		month = date.split(':')[1]
		day = date.split(':')[2]

		hour = time.split(':')[0]
		minute = time.split(':')[1]
		second = time.split(':')[2]
		if "+" in second:
			s = second
			second = s.split('+')[0]
			offset = s.split('+')[1] # timezone offset, we dont need it but someday we might?
		elif "-" in second: # i think there can be negative offsets too ?
			s = second
			second = s.split('-')[0]
			offset = s.split('-')[1]

		ext = os.path.splitext(f)[1]

		folder_path = os.path.join(out_dir, year, month)
		filename = year + "-" + month + "-" + day + "_" + hour + "." + minute + "." + second + ext
	else: # no date
		folder_path = os.path.join(out_dir, "Unknown Dates")
		filename = f

	final = os.path.join(folder_path, filename)
	return final

def copy_handler(input_path,destination):
	dest_folder = os.path.dirname(destination)

	if not os.path.isdir(dest_folder):
		os.makedirs(dest_folder)

	base = os.path.splitext( os.path.basename(destination) )[0]
	ext = os.path.splitext( os.path.basename(destination) )[1]
	if ext.lower() == ".jpeg": # change jpeg to jpg for consistency
		ext = ".jpg"

	i = 0
	new_name = base + "-" + str(i).zfill(2) + ext
	final_path = (os.path.join(dest_folder, new_name))
	while os.path.isfile(final_path):
		existing_file_hash = md5sum(final_path)
		new_file_hash = md5sum(input_path)

		if existing_file_hash == new_file_hash:
			return
		else:
			new_name = base + "-" + str(i).zfill(2) + ext # append letter to filename if it already exists
			final_path = (os.path.join(dest_folder, new_name))
		i += 1

	print("Copying", input_path, "-->", final_path)
	shutil.copy(input_path, final_path)

if os.path.isfile(already_processed_md5):
	with open(already_processed_md5) as f:
		lines = f.readlines()
	for line in lines:
		handled_md5s.append(line.rstrip())


# Main loop
for dirpath, dirnames, filenames in os.walk(in_dir):
	for f in tqdm(filenames, desc=dirpath):
		in_file = os.path.abspath(os.path.join(dirpath,f))
		ext = os.path.splitext(in_file)[1]

		if f in ignored_files or ext in ignored_file_exts:
			#print("Ignored:", f)
			continue # ignore

		if ext in video_exts and PICS_ONLY:
			continue
		elif ext not in video_exts and VIDS_ONLY:
			continue
	
		md5 = md5sum(in_file)
		if md5 in handled_md5s:
			#print("Duplicate hash:", f)
			continue
		
		info = grab_metadata(in_file)
		d = info['date']
		cID = info['content_ID']
		ext = os.path.splitext(in_file)[1]

		#if d:
		#	print("Date:", d)
		#if cID:
		#	print("Content ID:", cID)

		if cID: # has content id, could be a live photo
			if cID in contentID_IDs: # Found live photo?
				#print("This seems to be the other part of a Live Photo... let's copy them together")
				matched_filename = contentID_filenames[contentID_IDs.index(cID)]

				if ext.lower() == '.mov':
					video_path = in_file
					picture_path = matched_filename
				else:
					video_path = matched_filename
					picture_path = in_file

				info_pic = grab_metadata(picture_path)
				d_pic = info_pic['date']

				# copy video part
				dest = destination_from_date(d_pic, video_path)
				copy_handler(video_path, dest)
				# copy picture part
				dest = destination_from_date(d_pic, picture_path)
				copy_handler(picture_path, dest)


				contentID_IDs.remove(cID)
				contentID_filenames.remove(matched_filename)
			else:
				#print("This seems to be part of a Live Photo... let's wait for the other part before we do anything")
				contentID_filenames.append(in_file)
				contentID_IDs.append(cID)
				
		else:
			# no content id, just handle it regularly
			dest = destination_from_date(d, in_file)
			copy_handler(in_file, dest)

		handled_md5s.append(md5)


# now handle leftover files in contentID_filenames
if len(contentID_filenames) > 0:
	print("---")
	print("There are", len(contentID_filenames), "files with unpaired Content IDs left")
	for f in contentID_filenames:
		info = grab_metadata(f)
		d = info['date']
		#print('Input:', f)
		#if d:
		#	print(d)
		dest = destination_from_date(d, f)
		copy_handler(f, dest)
		#print('-')
	print("---")

# write handled_md5s
with open(already_processed_md5, "w") as f:
	for h in handled_md5s:
		f.write(h + "\n")

print("Done")
