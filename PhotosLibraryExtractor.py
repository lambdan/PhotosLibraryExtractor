import exiftool, sys, shutil, os, hashlib
#exiftool: http://github.com/smarnach/pyexiftool

in_dir = sys.argv[1]
out_dir = './out/'
already_processed_db = './.PhotosLibraryExtractor_ProcessedFiles'

in_dir = os.path.abspath(in_dir)
out_dir = os.path.abspath(out_dir)

if not os.path.isdir(out_dir):
	print("Making output folder:", out_dir)
	os.makedirs(out_dir)

contentID_filenames = [] # for Live Photos
contentID_IDs = []
handled_files = []
previously_handled_files = []
duplicate_files = []

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

	if 'EXIF:DateTimeOriginal' in metadata:
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

		ext = os.path.splitext(f)[1]

		folder_path = os.path.join(out_dir, year, month)
		filename = year + month + day + "-" + hour + minute + second + ext
	else: # no date
		folder_path = os.path.join(out_dir, "Unknown Dates")
		filename = f

	final = os.path.join(folder_path, filename)
	print("Destination:", final)
	#print("DIR NAME:", os.path.dirname(final))
	return final

def copy_handler(input_path,destination):

	dest_folder = os.path.dirname(destination)

	if not os.path.isdir(dest_folder):
		#print("Making folder:", dest_folder)
		os.makedirs(dest_folder)

	final_path = destination

	# check if file already exists, if so hash it
	# TODO just reuse the md5sum we got in the main loop isntead of redoing it here?

	i = 1
	base = os.path.splitext( os.path.basename(destination) )[0]
	ext = os.path.splitext( os.path.basename(destination) )[1]
	while os.path.isfile(final_path):
		#print("File already exists, incrementing number")

		print("Hmm, this file already exists:", final_path)
		print("Let's see if its identical to this file we're trying to copy:")
		existing_file_hash = md5sum(final_path)
		print("MD5 of existing file:\t", existing_file_hash)
		new_file_hash = md5sum(input_path)
		print("MD5 of new file:\t", new_file_hash)

		if existing_file_hash == new_file_hash:
			print("Yep, they're identical. Moving on...")
			return
		else:
			print("Oh! They're not identical! I'll copy the new file and add a number to it then. Let's try with number " + str(i) + ".")
			new_name = base + "-" + str(i) + ext
			final_path = (os.path.join(dest_folder, new_name))
		#print("Let's try with this instead:", final_path)
		i += 1

	print("Copying to:", final_path)
	shutil.copy(input_path, final_path)


def add_to_processed_files(filepath):
	if not os.path.isfile(already_processed_db):
		with open(already_processed_db, 'a') as sf:
			sf.write('# This is just a list of files that we have handled previously to speed up future runs\n')
			sf.write('# Feel free to delete it if you want to start over\n')

	with open(already_processed_db, 'a') as sf:
		sf.write(filepath + '\n')

# Use this for finding metadata tags
#with exiftool.ExifTool() as et:
#		metadata = et.get_metadata(sys.argv[1])
#print(metadata)
#EXIF:DateTimeOriginal
#EXIF:CreateDate
#EXIF:ModifyDate
#MakerNotes:ContentIdentifier
#QuickTime:CreateDate
#sys.exit(1)


# Read previously handled files
if os.path.isfile(already_processed_db):
	print("Reading", already_processed_db)
	with open(already_processed_db) as f:
		lines = f.readlines()
	for line in lines:
		previously_handled_files.append(line.rstrip())
	print(len(previously_handled_files), "files read from", already_processed_db)
	print("They will be skipped this run. If you want to start over, delete the file:", already_processed_db)
	print("---")

skipped_files = len(previously_handled_files)

# Main loop
for dirpath, dirnames, filenames in os.walk(in_dir):
	for f in filenames:
		if f == ".DS_Store": 
			continue # ignore .DS_Store files

		in_file = os.path.abspath(os.path.join(dirpath,f))

		if in_file in previously_handled_files:
			#print("Skipping because we have handled it before:", in_file)
			#print("-")
			continue

		print("Input:", in_file)

		
		md5 = md5sum(in_file)
		if md5 in handled_files:
			print("Duplicate file:", f)
			duplicate_files.append(in_file)
			add_to_processed_files(in_file)
			print("-")
			continue
		
		info = grab_metadata(in_file)
		d = info['date']
		cID = info['content_ID']
		ext = os.path.splitext(in_file)[1]

		if d:
			print("Date:", d)
		if cID:
			print("Content ID:", cID)

		if cID: # has content id, could be a live photo
			if cID in contentID_IDs: # Found live photo?
				print("This seems to be the other part of a Live Photo... let's copy them together")
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
				print("This seems to be part of a Live Photo... let's wait for the other part before we do anything")
				contentID_filenames.append(in_file)
				contentID_IDs.append(cID)
				
		else:
			# no content id, just handle it regularly
			dest = destination_from_date(d, in_file)
			copy_handler(in_file, dest)

		handled_files.append(md5)
		add_to_processed_files(in_file)
		print('-')


# now handle leftover files in contentID_filenames
print("There are", len(contentID_filenames), "files with unpaired Content IDs left")
for f in contentID_filenames:
	info = grab_metadata(f)
	d = info['date']
	print('Input:', f)
	if d:
		print(d)
	dest = destination_from_date(d, f)
	copy_handler(f, dest)
	print('-')
print("---")

skipped_files += len(duplicate_files)

print("New files:", len(handled_files))
print("Skipped files:", skipped_files)
#print("Ignored files (duplicates):", len(duplicate_files))