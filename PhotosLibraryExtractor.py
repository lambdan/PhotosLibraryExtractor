import exiftool, sys, shutil, os, hashlib
from argparse import ArgumentParser
#exiftool: http://github.com/smarnach/pyexiftool


# Use this for finding metadata tags
#with exiftool.ExifTool() as et:
#		metadata = et.get_metadata(sys.argv[1])
# 		sys.exit(1)

parser = ArgumentParser()
parser.add_argument('-i', action='store', dest='input', help='Folder with pictures you want to process a.k.a. input folder', required=True)
parser.add_argument('-o', action='store', dest='output', help='Photos will be copied to this folder a.k.a. output folder', required=True)
parser.add_argument('-db', action='store', dest='db_path', help='Path to PLEDB file', required=False)
parsed = parser.parse_args()

ignored_files = [".DS_Store", "PLEDB"]
ignored_file_exts = [".bat", ".sh", ".py", ".zip", ".7z"]

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
if parsed.db_path:
	already_processed_db = os.path.abspath(parsed.db_path)
else:
	already_processed_db = os.path.join(out_dir, 'PLEDB')

print("Input folder:", in_dir)
print("Destination:", out_dir)
print("DB file:", already_processed_db)
print("---")

if not os.path.isdir(in_dir):
	print("Error! This doesn't seem to be a folder:", in_dir)
	sys.exit(1)

if not os.path.isdir(out_dir):
	print("Making output folder:", out_dir)
	os.makedirs(out_dir)

contentID_filenames = [] # for Live Photos
contentID_IDs = []
handled_files = []
previously_handled_files = []
duplicate_files = []
files_copied = 0

def md5sum(filename):
	size = os.path.getsize(filename)

	h = hashlib.md5()
	with open(filename, 'rb') as file:
		chunk = 0
		while chunk != b'':
			chunk = file.read(1024)
			h.update(chunk)

	return h.hexdigest()

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
		filename = year + "-" + month + "-" + day + " " + hour + "." + minute + "." + second + ext
	else: # no date
		folder_path = os.path.join(out_dir, "Unknown Dates")
		filename = f

	final = os.path.join(folder_path, filename)
	return final

def copy_handler(input_path,destination):
	global files_copied
	dest_folder = os.path.dirname(destination)

	if not os.path.isdir(dest_folder):
		os.makedirs(dest_folder)

	base = os.path.splitext( os.path.basename(destination) )[0]
	ext = os.path.splitext( os.path.basename(destination) )[1]
	if ext.lower() == ".jpeg": # change jpeg to jpg for consistency
		ext = ".jpg"

	i = 97 # 97 is a
	new_name = base + ext
	final_path = (os.path.join(dest_folder, new_name))
	while os.path.isfile(final_path):
		existing_file_hash = md5sum(final_path)
		new_file_hash = md5sum(input_path)

		if existing_file_hash == new_file_hash:
			return
		else:
			new_name = base + chr(i) + ext # append letter to filename if it already exists
			final_path = (os.path.join(dest_folder, new_name))
		i += 1

	print(input_path, "-->", final_path)
	files_copied += 1
	shutil.copy(input_path, final_path)


def add_to_processed_files(filepath):
	with open(already_processed_db, 'a') as sf:
		sf.write(filepath + '\n')

# Read previously handled files
if os.path.isfile(already_processed_db):
	print("Reading", already_processed_db)
	with open(already_processed_db) as f:
		lines = f.readlines()
	for line in lines:
		previously_handled_files.append(line.rstrip())
	print(len(previously_handled_files), "files in PLEDB")
	print("They will be skipped this run. If you want to start fresh, delete the file:", already_processed_db)
	print("---")

skipped_files = len(previously_handled_files)

# Main loop
for dirpath, dirnames, filenames in os.walk(in_dir):
	for f in filenames:
		if f in ignored_files or os.path.splitext(f)[1].lower() in ignored_file_exts:
			print("Ignored:", f)
			continue # ignore

		in_file = os.path.abspath(os.path.join(dirpath,f))

		if in_file in previously_handled_files:
			continue
		
		md5 = md5sum(in_file)
		if md5 in handled_files:
			print("Duplicate:", f)
			duplicate_files.append(in_file)
			add_to_processed_files(in_file)
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

		handled_files.append(md5)
		add_to_processed_files(in_file)
		#print('-')


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

skipped_files += len(duplicate_files)

print("Files processed:", len(handled_files))
print("Files copied:", files_copied)
print("Skipped files:", skipped_files)
#print("Ignored files (duplicates):", len(duplicate_files))
print("Done")
