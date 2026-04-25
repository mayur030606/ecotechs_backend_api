import cv2
import numpy as np

def mse(imageA, imageB):
    # Mean Squared Error between the two images
    err = np.sum((imageA.astype("float") - imageB.astype("float")) ** 2)
    err /= float(imageA.shape[0] * imageA.shape[1])
    return err

def compare_images(img1_path, img2_path):
    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)

    if img1 is None or img2 is None:
        return 0.0, 0.0

    # Resize
    img1 = cv2.resize(img1, (500, 500))
    img2 = cv2.resize(img2, (500, 500))

    # Grayscale
    gray1 = cv2.cvtColor(img1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(img2, cv2.COLOR_BGR2GRAY)

    # Blur
    gray1 = cv2.GaussianBlur(gray1, (7, 7), 0)
    gray2 = cv2.GaussianBlur(gray2, (7, 7), 0)

    # MSE (higher means more difference)
    # Normalize it roughly to a 0-1 scale where 1 is completely different
    # Max MSE is 255^2 = 65025
    error = mse(gray1, gray2)
    difference = min(error / 10000.0, 1.0) # Cap at 1.0 for simplicity

    # ORB
    orb = cv2.ORB_create()
    kp1, des1 = orb.detectAndCompute(gray1, None)
    kp2, des2 = orb.detectAndCompute(gray2, None)

    match_score = 0.0

    if des1 is not None and des2 is not None and len(kp1) > 0 and len(kp2) > 0:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        match_score = len(matches) / max(len(kp1), len(kp2))

    return float(difference), float(match_score)
