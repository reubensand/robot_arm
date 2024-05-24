import cv2
import numpy as np
import matplotlib.pyplot as plt
from skimage.util import invert
from skimage.morphology import skeletonize
from skimage import color, img_as_bool
import math
# Standard Letter Paper size
PAPER_WIDTH = 8.5
PAPER_HEIGHT = 11


'''
Reuben De Souza
Junior Design II
Block 2 Demo

Description: This program takes in an image and outputs coordinates
             that when straight lines are drawn in between will recreate
             a recognizable approximation of the image. 

             The process for simple images is as follows:
             1. Convert to Boolean 
             2. Invert (white lines on black background)
             3. Skeletonize (single pixel width lines)
             4. Find contours of skeleton
             5. Approximate contours using polygons
             6. Organize polygons so that path between minimizes lines of the
                original image. (Since pen can't be picked up)

             The process for complex images is as follows:
             1. Blurs image to reduce noise
             2. Find edges using Canny edge dectection
             2. Find contours of edges
             5. Approximate contours using polygons
             6. Organize polygons so that path between minimizes lines of the
                original image. (Since pen can't be picked up)
 
             After either of these processes is completed, the image is displayed 
             for the user to confirm. Also, the approximated polygon contours are
             sent to the Arduino (printed to the screen for testing/demo). 
             
             The clarity of the approximation can be adjusted, and the corresponding
             number of points needed for the trace will be displayed.
'''

def get_dimensions(image):
    
    pixel_height, pixel_width = image.shape[:2]
    print(f'H: {pixel_height} W: {pixel_width}')
    # Calculate PPI for both dimensions
    ppi_width = pixel_width / PAPER_WIDTH
    ppi_height = pixel_height / PAPER_HEIGHT

    ppi = (ppi_width + ppi_height) / 2

    ppmm = ppi / 25.4
    return ppmm

def euclidean_distance(p1, p2): 
    '''
    Find the distance between two points:
    Parameters: p1 [x y], p1 [x y]
        x and y are int
    Returns: distance (float)
    '''
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def resize_image(image):
    '''
    Resize the image to fit with in US letter paper,
    while preserving aspect ratio
    Parameters: image (read using cv2.imread()) 
    Returns: resized image (cv2 image)
    '''
    aspect_ratio = PAPER_WIDTH / PAPER_HEIGHT
    height, width = image.shape[:2]
    new_width = min(width, int(height * aspect_ratio))
    new_height = min(height, int(width / aspect_ratio))
    resized_image = cv2.resize(image, (new_width, new_height))
 
    return resized_image

def find_closest_point(first, second):
    '''
    Given two contours it find the two points with the 
    shortest distance
    Parameters: first (cv2 contour), second (cv2 contour)
    Returns: point in first contour [x y], point in second contour [x y], 
    distance between them (float)
    '''
    first_point = None
    second_point = None
    closest_dist = float('inf')

    for point in first:
        for other_point in second:
            # Calculate distance between the points
            dist = euclidean_distance(point[0], other_point[0])
            # Update closest distance and point if this distance is smaller
            if dist < closest_dist:
                closest_dist = dist
                second_point = other_point
                first_point = point

    return first_point[0], second_point[0], closest_dist


def find_index_of_point(contour, point):
    '''
    Finds a the index of a specified point in a contour
    Parameters: contour (cv2 contour), point (form [x y])
    Returns: index (int)
    '''
    for i, contour_point in enumerate(contour):
        if (contour_point[0] == point).all():
            return i
    return -1  # Return -1 if point not found in contour
    
def send_array(contour, start, end, ppmm):
    '''
    This function will send the array over serial to Arudino
    It will start at the "start" index, loop through 
    entire array once, then loop through till "end" index
    Parameters: contour (cv2 contour), start (int), end (int)
    Returns: total number of points "sent"
    '''

    '''Alternate between X and Y values'''
    print()
    total = 1
    length = len(contour)
    for i in range(length):
        x, y = contour[(start + i) % length][0]
        x = x / ppmm
        y = y / ppmm
        print(f"X: {x:.1f} mm, Y: {y:.1f} mm")
        total = total + 1
    while start != end:
        x, y = contour[(start + i) % length][0]
        x = x / ppmm
        y = y / ppmm
        print(f"X: {x:.1f} mm, Y: {y:.1f} mm")
        total = total + 1
        start = (start + 1) % length

    x, y = contour[(start + i) % length][0]
    x = x / ppmm
    y = y / ppmm
    print(f"X: {x:.1f} mm, Y: {y:.1f} mm")

    return total

def contour_closeness(approximations):
    '''
    This function will find the path between contours that minimizes
    the distance between the end of one contour and start of another.
    The order will be placed in an array and the point (from, to) will
    be in another array

    Parameters: approximations (array of contours) 
    Returns: closest_points [array of [x y]], visited []
    '''
    closest_points = []  # List to store the closest points for each point in the first contour
    length = 0
    start_index = 0
    visited = [start_index]

    while length < len(approximations) - 1:
        min_dist = float('inf')
        best_index = None
        for i in range(len(approximations)):
            if i not in visited:
                x, y, dist = find_closest_point(approximations[start_index], approximations[i])
                if dist < min_dist:
                    min_dist = dist
                    best_index = i
                    form = x
                    to = y

        closest_points.append((form, to))

        visited.append(best_index)        
        start_index = best_index  # Update start_index to the best_index for the next iteration
        length += 1
    return closest_points, visited

def extract_points(approximations, closest_points, visited):
    '''
    This function finds the index of the start and end points that
    make the transition between contours "easy" (defined earlier).
    Adds the indices to separate arrays

    Parameters: approximations (array of contours), closest_points [array of [x y]], visited []
    Returns: start_indices [], end_indices []
    '''
    start_indices = []
    end_indices = [0]

    for i in range(len(approximations)-1):
        c_from = visited[i]
        c_to = visited[i+1]
        p_from = closest_points[i][0]
        p_to = closest_points[i][1]

        from_index = find_index_of_point(approximations[c_from], p_from)
        start_indices.append(from_index)
        to_index = find_index_of_point(approximations[c_to], p_to)
        end_indices.append(to_index)
    return start_indices, end_indices

def complex_img(image, clarity, ppmm):
    '''
    This is the main function that processes a complex image.
    Detailed above. 

    Parameters: image (cv2 image), clarity (optional)
    Clarity parameter has range [0.0001, 0.01]
    (0.005 maximizes contours and efficiency of points
    Returns: None
    '''
    # create image to draw final contours on
    blank = np.zeros_like(image)

    blurred = cv2.GaussianBlur(image, (5,5),0)

    edges = cv2.Canny(blurred, 50, 160)

    contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    total = 0
    approximations = []
    for _, contour in enumerate(contours): 
        approx = cv2.approxPolyDP(contour, clarity * cv2.arcLength(contour, True), True)
        total = total+len(approx)
        approximations.append(approx)

    closest_points, visited = contour_closeness(approximations)
    
    new_total = 0
    start_indices, end_indices = extract_points(approximations, closest_points, visited)
    start_indices.append(0)
    for i in range(len(approximations)):  
        new_total = new_total + send_array(approximations[visited[i]], end_indices[i], start_indices[i], ppmm)    

    for approx in approximations:
        cv2.drawContours(blank, [approx], -1, (0, 255, 0), 1)  # Green color for 

    print(new_total)
    plt.imshow(blank)
    plt.show()


def simple_img(image, clarity, ppmm):
    '''
    This is the main function that processes a simple image.
    Detailed above. 

    Parameters: image (cv2 image), clarity (optional)
    Clarity parameter has range [0.0001, 0.01]
    (0.005 maximizes contours and efficiency of points
    Returns: None
    '''
    # create image to draw final contours on
    blank = np.zeros_like(image)

    img = np.asarray(img_as_bool(color.rgb2gray(image)))
    img_inv = invert(img)

    # perform skeletonization
    skeleton = skeletonize(img_inv)
    
    # Convert skeleton back to uint8
    skeleton_uint8 = skeleton.astype(np.uint8) * 255

    total = 0
    contours, _ = cv2.findContours(skeleton_uint8, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)


    approximations = []
    for i, contour in enumerate(contours):
        if i != 0:    
            approx = cv2.approxPolyDP(contour, clarity * cv2.arcLength(contour, True), True)
            approximations.append(approx)
            total = total+len(approx)

    closest_points, visited = contour_closeness(approximations)
    
    start_indices, end_indices = extract_points(approximations, closest_points, visited)

    new_total = 0
    start_indices.append(0)
    for i in range(len(approximations)):  
        new_total = new_total + send_array(approximations[visited[i]], end_indices[i], start_indices[i], ppmm)    

    for approx in approximations:
        cv2.drawContours(blank, [approx], -1, (0, 255, 0), 2)  # Green color for

    print(new_total)
    plt.imshow(blank)
    plt.show()

def Process_img(filepath, complexity, clarity=0.01):
    image = cv2.imread(filepath)
    resize_img = resize_image(image)
    ppmm = get_dimensions(resize_img)

    if complexity.lower() == 'complex':
        complex_img(resize_img, clarity, ppmm)
    elif complexity.lower() == 'simple':
        simple_img(resize_img, clarity, ppmm)
    else:
        print("Failed to process")
    
'''Test Cases'''

flower_path = "C:\\Users\\reubs\\mitpractice\\jrdesign\\flower.jpg"
logo_path = "C:\\Users\\reubs\\mitpractice\\jrdesign\\logo.png"

# image_flower = cv2.imread(flower_path)
# # image_logo = cv2.imread(logo_path)

# resize_flower = resize_image(image_flower)
# ppmm = get_dimensions(resize_flower)
# simple_img(resize_flower, 0.01, ppmm)

# resize_logo = resize_image(image_logo)
# complex_img(resize_logo)

# resize_logo = resize_image(image_logo)
# complex_img(resize_logo, clarity=0.0001)
