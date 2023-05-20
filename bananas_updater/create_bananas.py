from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
import random as rd
from django.utils import timezone
import os
import time
from datetime import datetime, timedelta

from django_project.settings import BASE_DIR
from find_bananas.models import Bananas

outfile = os.path.join(BASE_DIR, 'find_bananas/static/images/banana_thumbnail.png')
outfile_rotated = os.path.join(BASE_DIR, 'find_bananas/static/images/banana_thumbnail_rotated.png')


def is_locked(filepath):
  locked = None
  file_object = None
  if os.path.exists(filepath):
    print("Le path existe")
    try:
      buffer_size = 8
      # Opening file in append mode and read the first 8 characters.
      file_object = open(filepath, 'a', buffer_size)
      if file_object:
        print("Le file est utilisable")
        locked = False
    except IOError as message:
      print("Le file est locked")
      locked = True
    finally:
      if file_object:
        file_object.close()
  return locked

def wait_for_file(filepath):
  wait_time = 1
  while is_locked(filepath):
    time.sleep(wait_time)
    print("On vient de faire un time sleep de 1 seconde")



def bananas_of_the_day(first_time = False):

  now = datetime.now()
  offset = timedelta(hours=2)  # Fuseau horaire français : UTC+2
  now_france = now + offset
  date = now_france.strftime("%Y-%m-%d-%H-%M-%S")

  image1 = os.path.join(BASE_DIR, f'find_bananas/static/images/bananas_of_the_day_round1_{date}.png')
  image2 = os.path.join(BASE_DIR, f'find_bananas/static/images/bananas_of_the_day_round2_{date}.png')
  image3 = os.path.join(BASE_DIR, f'find_bananas/static/images/bananas_of_the_day_round3_{date}.png')

  img_thumb = Image.open(outfile, 'r').convert("RGBA")

  background1 = Image.new('RGBA', (1440, 900), (255, 255, 255, 255))
  background2 = Image.new('RGBA', (1440, 900), (255, 255, 255, 255))
  background3 = Image.new('RGBA', (1440, 900), (255, 255, 255, 255))
  bg_w, bg_h = background1.size

  nb_bananas_round1 = rd.randint(20, 50)
  nb_bananas_round2 = rd.randint(50, 100)
  nb_bananas_round3 = rd.randint(100, 200)

  for i in range(nb_bananas_round1):
    img_thumb = Image.open(outfile, 'r').convert("RGBA")
    img_thumb.rotate(rd.randint(0, 360), expand=True).save(outfile_rotated)
    img_thumb_rotate = Image.open(outfile_rotated, 'r').convert("RGBA")
    img_w, img_h = img_thumb_rotate.size
    background1.paste(img_thumb_rotate, (rd.randint(0, 1440-img_w), rd.randint(0, 900-img_h)), img_thumb_rotate)
    img_thumb_rotate.close()

  for i in range(nb_bananas_round2):
    img_thumb = Image.open(outfile, 'r').convert("RGBA")
    img_thumb.rotate(rd.randint(0, 360), expand=True).save(outfile_rotated)
    img_thumb_rotate = Image.open(outfile_rotated, 'r').convert("RGBA")
    img_w, img_h = img_thumb_rotate.size
    background2.paste(img_thumb_rotate, (rd.randint(0, 1440-img_w), rd.randint(0, 900-img_h)), img_thumb_rotate)
    img_thumb_rotate.close()

  for i in range(nb_bananas_round3):
    img_thumb = Image.open(outfile, 'r').convert("RGBA")
    img_thumb.rotate(rd.randint(0, 360), expand=True).save(outfile_rotated)
    img_thumb_rotate = Image.open(outfile_rotated, 'r').convert("RGBA")
    img_w, img_h = img_thumb_rotate.size
    background3.paste(img_thumb_rotate, (rd.randint(0, 1440-img_w), rd.randint(0, 900-img_h)), img_thumb_rotate)
    img_thumb_rotate.close()

  #background.show()
  background1.save(image1)
  background2.save(image2)
  background3.save(image3)

  dico_bananas = {
    "round1": {"number": nb_bananas_round1, "image": image1},
    "round2": {"number": nb_bananas_round2, "image": image2},
    "round3": {"number": nb_bananas_round3, "image": image3}
  }
  try:
    if first_time == False:
      Bananas.objects.latest('timestamp').delete()
    new_bananas = Bananas()
    new_bananas.timestamp = now_france
    new_bananas.date = date
    new_bananas.nb_bananas_1 = dico_bananas["round1"]["number"]
    new_bananas.nb_bananas_2 = dico_bananas["round2"]["number"]
    new_bananas.nb_bananas_3 = dico_bananas["round3"]["number"]
    new_bananas.image_1 = dico_bananas["round1"]["image"]
    new_bananas.image_2 = dico_bananas["round2"]["image"]
    new_bananas.image_3 = dico_bananas["round3"]["image"]
    new_bananas.save()
    print("New bananas created")

  except Exception as e:
    print(e)
    pass
  #return dico_bananas

