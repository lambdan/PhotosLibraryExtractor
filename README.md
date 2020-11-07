# Photos.app Library Extractor

Exports photos from macOS Photos.app Library to Year/Month folders with dates as filenames. Perfect for a local offline backup.

Specifically made for macOS Photos.app libraries, as it can match Live Photos by looking at their Content ID tags, but it works for generic folders of photos too.

Basically, you go from this:

![Before](https://raw.githubusercontent.com/lambdan/PhotosLibraryExtractor/main/Screenshots/Screenshot%202020-11-07%20at%2011.34.21.png)

To this:

![After](https://raw.githubusercontent.com/lambdan/PhotosLibraryExtractor/main/Screenshots/Screenshot%202020-11-07%20at%2011.35.28.png)

## Why not just use the "Export Unmodified Originals" option in Photos.app?

In my experience:

- I frequently get non-descript errors doing that
- It's slow
- The filenames aren't what I want
- You can't practically extract all at once, you need to make Smart Albums by years or so to get smaller batches

But feel free to try that option yourself. Maybe it's good for you!

## What is the structure of the Photos.app Library?

The `Photos Library.photoslibrary` is basically a folder! If you right click it in macOS you can choose "Show Package Contents" and in there you find folders. 

Most interesting to us is the originals folder as that folder seems to contain unmodified original files. 

Unfortunately, inside the originals folder is a mess of scary folders and scary file names that are essentially random. Luckily for us, the files themselves seem to be untouched and contain a lot of metadata which we can read, such as the date the photo was taken, which we can use to get a nicer filename.

## How are Live Photos paired?

Apple conveniently has a Content ID that pairs the photo and video component. Just read the tags and if it's the same Content ID: it's a pair. 

Unfortunately, the photo's date is in one timezone and the video's date is in another, so this script sets the filename of the video based on the photos date, so that both the photo and video file have the same filenames except for the extension.

Here you can see a screenshot of how the script handles Live Photos: 

![Live Photos](https://raw.githubusercontent.com/lambdan/PhotosLibraryExtractor/main/Screenshots/Screenshot-%20Handling%20live%20photo.png)

(Notice how the dates are two hours off from each other and that the MOV gets the same filename as the JPG.)

## Is this safe?

It should be. I don't modify anything inside the input folder. I just read it and copy from it.

## How are duplicates handled?

Every input file gets hashed using MD5. If it's a hash we've already had, the file is skipped. 

If the destination file already exists, the new file and the existing file gets MD5 hashed and compared to see if they're identical, and if so, the new file isn't copied.

But if the destinaton file already exists, and the MD5 hashes aren't identical the new file is copied with a number appended to it. In case that the new filename with a number appended to it is also already existing then we also MD5 compare them, and so until we either find a identical match or we find a free filename.

You're meant to be able to re-use the same input and output folders repeatedly without re-doing the work every time.

Here you can see a screenshot of what happens then the destination file(s) already exist: 
![Destination Exists](https://raw.githubusercontent.com/lambdan/PhotosLibraryExtractor/main/Screenshots/Screenshot%20-%20handling%20duplicate%20destination.png)

## How do I use this?

I've only tested it on macOS (because it is meant for the Photos.app library afterall), but I don't see any reason why it wouldn't work on Windows or Linux.


### Preparing in Photos.app

Make sure you have the "Download Originals to this Mac" option enabled in Photos.app: 

![Download Originals](https://raw.githubusercontent.com/lambdan/PhotosLibraryExtractor/main/Screenshots/Download%20Originals.png)

Make sure your Photos are completely downloaded and up to date (the bottom of the Photos tab in Photos.app should just "Updated" or something similar): 

![Updated](https://raw.githubusercontent.com/lambdan/PhotosLibraryExtractor/main/Screenshots/Screenshot%202020-11-07%20at%2013.32.30.png)

### Prerequisites

- This script is written using Python 3, so make sure you have that
- I use [exiftool](https://exiftool.org) to read metadata from the images, so make sure you have that installed and accessible through the command line
    - If you're on macOS you can use [Brew](https://brew.sh) to install it: `brew install exiftool` 
- The script uses the Python library [pyexiftool](https://github.com/smarnach/pyexiftool) to use exiftool
    - Apparently, you can install that library using pip, but that didn't work for me (I get import module error). What worked for me was just having the `exiftool.py` file in the same folder as this script 

### Changing Settings

If you wanna edit the output folder or the date format or folder structure or anything like that, edit the script to your liking. (Ideally I should make this nicer, but I think my defaults are pretty sane, so it's not a high priority)

- By default the output folder (the organized folder) is in a folder called `out` in your current working folder
- The folder structure is `YYYY/MM`, along with a folder called `Unknown Dates` for photos with... yep, unknown dates
- The filename structure is `YYYYMMDD-HHMMSS.ext` with a number added if its an already existing file, like `YYYYMMDD-HHMMSS-1.ext`

### Running the Script

Run the script: 
    
    python3 PhotosLibraryExtractor.py /folder/with/pictures/

If you are processing a Photos.app Library you should use the `originals` sub folder: 

    python3 PhotosLibraryExtractor.py "~/Photos/Photos Library.app/originals/

The script is very verbose, almost annoyingly so, because these are highly valuable photos we are dealing with and I want you to know exactly what is going on.

### Future Runs

Future runs will skip previously processed files. The first run for me with my 12000 photos took about 1 hour to finish on my 13-inch MacBook Pro (my Photo Library is on a mechanical drive though so that probably didn't help). Future runs where just a couple of photos was added was done in a matter of seconds. 

### Starting Over

If you want to start over and not skip any files, you can remove the `.PhotosLibraryExtractor_ProcessedFiles` file. It's just a simple file with one filepath per line, so you can even just remove the one file you don't want to be skipped if you can find it in there.

## What's up with these leftover unpaired IDs?

I'm guessing these are Live Photos were the video component of them was removed at some point which I don't remember. There shouldn't be too many. In my library of over 10000 items, I got 16.

The unpaired ID's are copied into the destination folder anyway, so you won't lose anything. You can see when the script processes them which paths they have so you can investigate if you want to, but I wouldn't worry about it.

## I got a lot of files in the "Unknown Dates" folder. What do I do?

For me, most of them were screenshots, photos I saved from Snapchat, or photos I saved to the library from the internet or Twitter. 

There could however be some genuine photos in there too, like if your camera didn't have a date set or something. 

So it is unfortunately a thing I can't really help you with. I would just keep it around in case there is anything important in there.