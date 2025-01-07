import cv2
import cv2.aruco as aruco
import numpy as np

VideoCap = False
cap = cv2.VideoCapture(1, cv2.CAP_V4L2)
dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_6X6_250)
parameters = cv2.aruco.DetectorParameters()
detector = cv2.aruco.ArucoDetector(dictionary, parameters)
liste_aruco=[]

# Nos valeurs de calibration
donnees=np.load("src/vision/calibration_params.npz")
mtx = cameraMatrix = donnees['cameraMatrix']
dist = donnees['distCoeffs']
known_width = 0.05

# def drawMarker(img, corners, distance, color=(0, 255, 0)):
#     corners = np.array([corners[0], corners[3]], dtype=np.int32).reshape((-1, 1, 2))
#     cv2.polylines(img, [corners], True, color)
#     center = tuple(np.mean(corners, axis=0, dtype=np.int32).ravel())

# def findAruco(img, marker_size=6, draw=True):
    
#     if markerI
        

#         undistorted_corners = cv2.undistortPoints(corners, mtx, dist)

        # On va calculer la distance
        # known_width = 0.05
        # focal_length = mtx[0, 0]
        # marker_width_pixels = np.linalg.norm(corners[0] - corners[1])
        #distance = (known_width * focal_length) / marker_width_pixels

        #rvecs, tvecs = estimatePoseSingleMarkers(obj_points, corners.astype(float), mtx, dist)
        # Afficher la distance

        # drawMarker(img, undistorted_corners, distance)
        # return distance,markerIds[0][0],tvec[0][0]

while True:
    _, img = cap.read()
    gray=cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    markerCorners, markerIds, rejectedCandidates = detector.detectMarkers(img)
    if markerIds is not None :
        for i in range(len(markerIds)):
                marker_points = np.array([[-marker_size/2,  marker_size/2, 0],
                                          [marker_size/2,   marker_size/2, 0],
                                          [marker_size/2,  -marker_size/2, 0],
                                          [-marker_size/2, -marker_size/2, 0]], dtype=np.float32)
                a, rvec, tvec = cv2.solvePnP(marker_points, markerCorners[i], mtx, dist, False, cv2.SOLVEPNP_IPPE_SQUARE)
                distance = tvec[2][0]  # Distance en mètres
                theta=np.arctan((tvec[0][0])/tvec[2][0])
                phi=rvec[2][0] + np.pi/2
                liste_aruco.append((distance,theta,phi,markerIds[i][0]))
         

# Undistort the image
    # undistorted_img = cv2.undistort(img, mtx, dist)

    # if cv2.waitKey(1) == 113:  # Check for 'q' key press
    #     break

    # cv2.imshow("img", img)

# cap.release()
# cv2.destroyAllWindows()