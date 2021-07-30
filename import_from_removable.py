# Simple script to:
# 1. Find mounted drives on a windows computer
# 2. Guess the camera type, if there are photos on there.
# 3. Copy to a NAS drive organised in to folders of cameratype/date.

from glob import glob
import psutil
import os
import exifread
from datetime import datetime
import logging
import win32file

out_path = r'S:\Photos'

def copyfile(src, dst):
	# Benchmarked on wifi network, native windows copy is fastest.
  #call(["echo", "f", "|", "xcopy", src, dst, "/Y"]) Fastish, 300mbit.
  #shutil.copyfile(src, dst) - sloooowwww, like 40mbit.
  win32file.CopyFile(src,dst,0) # Fastest BY FAR. 400mbps on home network.
	
# Get mount points for all removalable disks:
def get_mountpoints():
  logging.debug('Getting mount points')
  mounts = [e.mountpoint for e in psutil.disk_partitions() if 'removable' in e.opts]
  logging.debug('Found %s mounts', len(mounts))
  return mounts

# Guess camera type:
def camera_type(mountpoint):
  try:
    logging.debug('Looking for MISC\\version.txt on SD card to check if it\'s a GoPro')
    gopro_version_file = os.path.join(mountpoint, 'MISC', 'version.txt')
    with open(gopro_version_file, 'r') as data_file:    
      logging.debug('reading in contents of version.txt')
      data = data_file.readlines()
    
    logging.debug('scanning through all lines in version.txt')
    for line in data:
      if 'camera type' not in line:
        logging.debug('not the line we want: %s', line)
        continue
      
      logging.debug('found our model line: %s', line)
      gopro_model = line.split('"')[3]
      logging.debug('model is %s', gopro_model)
      break
    return 'GoPro ' + gopro_model
  except:
    pass
   
  # It's not a gopro if we're here, look for some jpegs to get the exif data
  logging.debug('mount is not from a gopro')
  try:
    logging.debug('Finding all Jpegs to check EXIF data')
    filelist = glob(os.path.join(mountpoint, 'DCIM', '*', '*.JPG'))
    logging.debug('opening first file %s', filelist[0])
    with open(filelist[0], 'rb') as f:
      logging.debug('Processing exif data in file')
      exif_data = exifread.process_file(f)
      model = exif_data['Image Model'].values
      logging.debug('Model is a %s', model)
      return model
  except:
    pass
  
  # Default camera, my usual.
  logging.debug('Gopro and Exif checks have failed, assuming Canon EOS M6 Mk2')
  return ('Canon EOS M6 II')

  
def get_file_dates(file):
  logging.debug('Checking date on %s', file)
  photodate = datetime.fromtimestamp(os.stat(file).st_ctime)
  return photodate.year, photodate.month, photodate.day

  
def get_file_list(mount, file_types=['JPG','CR2','CR3','MP4']):
  logging.debug('creating file list')
  filelist = []
  for type in file_types:
    logging.debug('looking for %s files', type)
    filelist.extend(glob(os.path.join(mount, 'DCIM', '*', '*.'+type)))
  logging.info('found %s files to copy on %s', len(filelist), mount)
  return filelist
  
  
def main():
  logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)
  
  for mount in get_mountpoints():
    logging.info('Trying ' + mount)
    camera = camera_type(mount)
    logging.info(mount + ' is ' + camera)
    if 'Unknown Camera' in camera:
      logging.info('Unknown camera, moving on to next')
      continue
      
    filelist = get_file_list(mount)
    
    for source_file in filelist:
       year, month, day = get_file_dates(source_file)
       logging.debug('%s has date of %s/%s/%s', source_file, year, month, day)
       
       extension = os.path.splitext(source_file)[1][1:]
       logging.debug('%s extention is %s', source_file, extension)
       
       source_filename = os.path.basename(source_file)
       destination_path = os.path.join(out_path, camera, str(year), str(month).rjust(2,'0'), str(day).rjust(2,'0'), extension)
       
       logging.debug('checking if destination %s exists', destination_path)
       if not os.path.exists(destination_path):
         logging.debug('creating %s', destination_path)
         try:
           os.makedirs(destination_path)
         except Exception as e:
           logging.critical('Unable to create directory %s', destination_path)
           print(e)
           quit()
       
       destination_file = os.path.join(destination_path, source_filename)
  
       logging.info('copying from %s to %s', source_file, destination_file)
       try:
         copyfile(source_file, destination_file) # Was shutil.copy, but that's slow.
       except Exception as e:
         logging.critical('Error copying to %s!', destination_file)
         print(e)
         quit()
    logging.info('Copy for %s complete!', mount)
  logging.info('All copying finished.')
    
if __name__ == '__main__':
  main()
