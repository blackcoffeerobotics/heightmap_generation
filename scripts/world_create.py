#!/usr/bin/python3
import rospkg
import yaml
import xml.etree.ElementTree as ET
import os
import sys
import PIL
from PIL import Image, ImageOps
import shutil


img_size = 129
heightmap_side_length = 10
max_height = 5

master_string = ""
model_name = "heightmap"

world_template = """

<sdf version="1.5">
  <world name="default">

<scene>
  <sky>
    <clouds>
      <speed>50</speed>
    </clouds>
  </sky>
    <ambient>0 0 0 1.0</ambient>
    <shadows>0</shadows>
</scene>


<include>
    <uri>model://sun</uri>
    <pose>0 0 0 0 0 0</pose>
</include>

%s

  </world>
</sdf>

"""

model_template = """
<include>
    <uri>model://{}</uri>
    <name>{}</name>
    <pose>{} {} {} 0 0 0</pose>
</include>
"""


def rescale_and_resize(img_name, img_size):

    # Open image
    img = Image.open(img_name)

    if invert:
        img = ImageOps.grayscale(img)
        # img = ImageOps.invert(img)

        # Binary Thresholding in PIL

        threshold = 230
        # Resize image
        img = img.resize((int(img_size), int(img_size)), PIL.Image.ANTIALIAS)

        def fn(x):
            if x > threshold:
                return 0
            else:
                return 255
        img = img.convert('L').point(fn, mode='1')
    # Get data from image
    img_list = list(img.getdata())

    # Find minimum and maximum value pixels in the image
    img_max = max(img_list)
    img_min = min(img_list)

    # Determine factor to scale to a 8-bit image
    scale_factor = 255.0 / (img_max - img_min)

    img_list_new = [0] * img_size * img_size

    # Rescale all pixels to the range 0 to 255 (in line with unit8 values)
    for i in range(0, img_size):
        for j in range(0, img_size):
            img_list_new[i * img_size + j] = \
                int((img_list[i * img_size + j] - img_min) * scale_factor)
            if (img_list_new[i * img_size + j] > 255) \
                    or (img_list_new[i * img_size + j] < 0) \
                    or (img_list_new[i * img_size + j] -
                        int(img_list_new[i * img_size + j]) != 0):
                print("img_list_new[%d][%d] = %r" %
                      (i, j, img_list_new[i * img_size + j]))

    img.putdata(img_list_new)

    # Convert to uint8 greyscale image
    img = img.convert('L')

    # Save image
    img.save(img_name)

    img.close()


def yaml_loader():
    global img_size, heightmap_side_length, max_height

    with open(yaml_path) as file:
        params = yaml.full_load(file)
        img_size = params['size']
        heightmap_side_length = params['side_length']
        max_height = params['max_height']


def world_creator():
    global master_string, world_template, model_template, img_size

    if img_size != 0:
        temp_heightmap = model_template.format(
            model_name, model_name, str(0), str(0), str(0))
    else:
        temp_heightmap = ""
    master_string += temp_heightmap

    parser = ET.XMLParser()
    tree = ET.ElementTree(ET.fromstring(world_template %
                                        master_string, parser=parser))

    tree.write(world_path)


def write_heightmap_model(heightmap_path):
    global img_size, package_path
    rescale_and_resize(heightmap_path, img_size)

    config_template = read_template(package_path + "/config/templates/config.txt")
    write_config_file(config_template)
    shutil.copyfile(heightmap_path, package_path +
                    "/config/models/%s/%s.png" % (model_name, model_name))

    model_template = read_template(
        package_path + "/config/templates/heightmap_sdf.txt")
    write_sdf_file(model_template)
    # sdf_template = read_template(package_path+"config/template/heightmap_sdf.txt")


def write_config_file(config_template):

    creator_name = "gaurav"
    email = "contact@blackcoffeerobotics.com"
    description = "heightmap model"

    model_path = package_path + "/config/models/%s" % model_name
    shutil.rmtree(model_path)
    os.mkdir(model_path)
    # Replace indicated values
    config_template = config_template.replace("$MODELNAME$", model_name)
    config_template = config_template.replace("$AUTHORNAME$", creator_name)
    config_template = config_template.replace("$EMAILADDRESS$", email)
    config_template = config_template.replace("$DESCRIPTION$", description)

    # Ensure results are a string
    config_content = str(config_template)

    # Open config file
    target = open(model_path + "/model.config", "w")

    # Write to config file
    target.write(config_content)

    # Close file
    target.close()


def write_sdf_file(sdf_template):
    global heightmap_side_length, max_height

    # Ask for desired dimensions and heights of the Gazebo model
    size_x = str(heightmap_side_length)
    size_y = str(size_x)
    size_z = str(max_height)

    model_path = package_path + "/config/models/" + model_name

    # Filling in content
    sdf_template = sdf_template.replace("$FILENAME$", model_name)
    sdf_template = sdf_template.replace("$SIZEX$", size_x)
    sdf_template = sdf_template.replace("$SIZEY$", size_y)
    sdf_template = sdf_template.replace("$SIZEZ$", size_z)

    # Ensure results are a string
    sdf_content = str(sdf_template)

    # Open file
    target = open(model_path + "/model.sdf", "w")

    # Write to model.sdf
    target.write(sdf_content)

    # Close file
    target.close()


def read_template(temp_file_name):
    # Open template
    temp_file = open(temp_file_name, "r")

    # Read template
    temp_hold_text = temp_file.read()
    template = str(temp_hold_text)

    # Close template
    temp_file.close()

    return template


if __name__ == '__main__':

    arg_list = sys.argv

    world_name = arg_list[1]
    invert = False
    if (len(arg_list) > 2):
        flag = arg_list[2]
        if (flag == "invert"):
            invert = True

    rospack = rospkg.RosPack()
    package_path = rospack.get_path('heightmap_generation')
    yaml_path = package_path + "/config/heightmaps/config.yaml"
    world_path = package_path + "/config/worlds/" + world_name
    heightmap_path = package_path + "/config/heightmaps/%s.png" % model_name

    os.system("touch %s" % world_path)

    yaml_loader()
    if img_size > 0:
        write_heightmap_model(heightmap_path)

    world_creator()

    # Double inversion for image preservation

    # rescale_and_resize(heightmap_path, img_size)
    print('Done')
