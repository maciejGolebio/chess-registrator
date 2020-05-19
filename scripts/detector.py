import cv2
import numpy as np
import random
import math


class Detector():

    def __init__(self):
        self.center = None
        self.angle = None
        self.size = None

    def _show_image(self, image):
        scale_percent = 100

        # calculate the 50 percent of original dimensions
        width = int(image.shape[1] * scale_percent / 100)
        height = int(image.shape[0] * scale_percent / 100)

        # dsize
        dsize = (width, height)
        normalsize = cv2.resize(image, dsize)
        cv2.imshow('imgage', normalsize)
        if cv2.waitKey(0) & 0xff == 27:
            cv2.destroyAllWindows()

    def prepare(self, image):

        blur = cv2.GaussianBlur(image, (5, 5), 0)
        # sharpen_kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
        # sharpen = cv2.filter2D(blur, -1, sharpen_kernel)
        ret, th = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        canny = cv2.Canny(blur, 0, ret)
        kernel = np.ones((5, 5), np.uint8)
        dilation = cv2.dilate(canny, kernel, iterations=1)
        return dilation

    def _draw_contours_and_show(self, image, cnts):
        for c in cnts:
            box = cv2.boxPoints(c)
            box = np.int0(box)
            cv2.drawContours(image, [box], 0, (0, 0, 255), 2)
        cv2.imshow('image', image)

    """
    def _draw_squares(self, image, cnts):
        min_area = 4500
        max_area = 5200
        # squares = []
        for c in cnts:
            approx = cv2.approxPolyDP(c, 0.05 * cv2.arcLength(c, True), True)
            area = cv2.contourArea(c)

            if 3 < len(approx) <= 5 and (min_area < area < max_area or area > 60 * max_area):
                # x, y, w, h = cv2.boundingRect(approx)
                # cv2.rectangle(image, (x, y), (x + w, y + h), (252, 186, 3), 2)
                # rect = cv2.minAreaRect(c)
                # box = cv2.boxPoints(rect)
                # ox = np.int0(box)
                cv2.drawContours(image, c, 0, (0, 0, 255), 2)
                # squares.append(box)
        cv2.imshow('image', image)
        cv2.waitKey()
        """

    def _find_square(self, image):
        """"
        :returns:  squares with area with simialr to chess field, and chessboard - suspected squares
                    hierarchy - just hierarchy of squares, squares[i] is correlated with hierarchy[i], i(-1, inf+)
        """
        # prepared = self.prepare(image)
        # cv2.imshow('prepared', prepared)
        cnts, hier = cv2.findContours(image, cv2.RETR_TREE, cv2.CHAIN_APPROX_TC89_KCOS)
        # print(hier)
        # cnts = cnts[0] if len(cnts) == 2 else cnts[1]
        min_area = 4500
        max_area = 5500
        squares = []
        hierarchy = []
        for c, h in zip(cnts, *hier):
            approx = cv2.approxPolyDP(c, 0.05 * cv2.arcLength(c, True), True)
            rect = cv2.minAreaRect(c)
            # area = cv2.contourArea(c)
            area = rect[1][0] * rect[1][1]
            if 3 < len(approx) <= 6 and (min_area < area < max_area or 80 * max_area > area > 64 * min_area):
                rect = cv2.minAreaRect(c)
                squares.append(rect)
                hierarchy.append(h)

        return squares, hierarchy

    def _find_board(self, squares):
        if len(squares) > 0:
            return max(squares, key=lambda x: x[1][0])
        else:
            return None

    def _crop_board(self, image, board):
        cropped = None
        if board == None:
            pass
        else:
            center, size, angle = board[0], board[1], board[2] % 90
            center, size = tuple(map(int, center)), tuple(map(int, size))
            height, width = image.shape[0], image.shape[1]
            rot_matrix = cv2.getRotationMatrix2D(center, angle, 1)
            rotated = cv2.warpAffine(image, rot_matrix, (width, height))
            cropped = cv2.getRectSubPix(rotated, size, center)
            self.center = center
            self.angle = angle
            self.size = size
        return cropped

    def _prepare_lines(self, preapred_image):
        lines = cv2.HoughLines(preapred_image, 1, np.pi / 2, 255, None, 0, 0)
        detected_lines = []
        for i in lines:
            for rho, theta in i:
                a = np.cos(theta)
                b = np.sin(theta)
                x0 = a * rho
                y0 = b * rho
                x1 = int(x0 + 1000 * (-b))
                y1 = int(y0 + 1000 * a)
                x2 = int(x0 - 1000 * (-b))
                y2 = int(y0 - 1000 * a)
                detected_lines.append([(x1, y1), (x2, y2)])

        return detected_lines

    def _group_line(self, lines):
        pionowe = []
        poziome = []
        for line in lines:
            x1, y1, x2, y2 = line[0][0], line[0][1], line[1][0], line[1][1]
            if abs(x1 - x2) >= 5:
                poziome.append(line)
            else:
                pionowe.append(line)
        pionowe.sort(key=lambda x: x[0][0])
        poziome.sort(key=lambda y: y[0][1])
        return poziome, pionowe

    def _find_pivot_and_dist(self, set, param, key):
        """"
        :param: set -> zbiór lini poziomych/pionowych
        :param: value of width/height
        :param: key -> klucze - x to 0, y to 1

        :returns elem środkowy i dystans pomięc liniami szachownicy
        """
        # find pivot and dist
        nearest_to_middle: int = 0
        how_close = math.inf

        for i in range(len(set)):
            if abs(set[i][0][key] - (param / 2)) <= how_close:
                how_close = abs(set[i][0][key] - param / 2)
                nearest_to_middle = i
                # cv2.line(cdst, pionowe[nearest_to_middle][0], pionowe[nearest_to_middle][1], (0, 0, 255), 1)

        # distance from pivot to next
        dist = -1
        mean = 0
        counter = 0
        for i in range(len(set)):
            if param / 8 > set[i][0][key] - set[nearest_to_middle][0][key] >= param / 10:
                dist = set[i][0][key] - set[nearest_to_middle][0][key]
                mean += dist
                counter += 1

        dist = mean // counter
        return nearest_to_middle, dist

    def _filter_vertical_lines(self, pionowe, width):
        # find pivot and dist
        nearest_to_middle, dist = self._find_pivot_and_dist(pionowe, width, 0)
        print('dist:= ' + str(dist))
        for i in range(len(pionowe) - 1):
            if dist * 1.4 > abs(pionowe[i][0][0] - pionowe[i + 1][0][0]) > dist * .8:
                # cv2.line(cdst, pionowe[i][0], pionowe[i][1], (0, 0, 255), 1)
                pass
            else:
                pionowe[i] = None

        pionowe = list(filter(lambda x: x is not None, pionowe))
        return pionowe, dist

    def _filter_horizontal_lines(self, poziome, height):
        nearest_to_middle, dist = self._find_pivot_and_dist(poziome, height, 1)
        # counter: int = 0
        for i in range(len(poziome) - 1):
            # if counter == 9:
            #     poziome[i] = None
            #     break
            if dist * 1.4 > abs(poziome[i][0][1] - poziome[i + 1][0][1]) > dist * .8:
                # cv2.line(cdst, pionowe[i][0], pionowe[i][1], (0, 0, 255), 1)
                # counter += 1

                pass
            else:
                poziome[i] = None

        poziome = list(filter(lambda x: x is not None, poziome))
        return poziome, dist

    def _vertical_lines_reconstruction(self, lines: list, dist, board_img_width):
        while len(lines) < 9:
            lines.sort(key=lambda x: x[0][0])
            tmp_len = len(lines)
            for i in range(tmp_len):
                # lower bound
                if lines[i][0][0] > dist and abs(lines[i][0][0] - lines[i - 1][0][0]) > 1.4 * dist:
                    tmp = [(lines[i][0][0] - dist, lines[i][0][1]), (lines[i][1][0] - dist, lines[i][1][1])]
                    lines.append(tmp)
                # upper bound
                if board_img_width - lines[i][0][0] > dist:
                    tmp = None
                    if i == tmp_len - 1:
                        tmp = [(lines[i][0][0] + dist, lines[i][0][1]), (lines[i][1][0] + dist, lines[i][1][1])]
                    elif lines[i + 1][0][0] - lines[i][0][0] > 1.4 * dist:
                        tmp = [(lines[i][0][0] + dist, lines[i][0][1]), (lines[i][1][0] + dist, lines[i][1][1])]
                    if tmp is not None:
                        lines.append(tmp)

    def _horizontal_lines_reconstruction(self, lines: list, dist, board_img_height):
        while len(lines) < 9:
            lines.sort(key=lambda x: x[0][1])
            tmp_len = len(lines)
            for i in range(tmp_len):
                if lines[i][0][1] > dist and abs(lines[i][0][1] - lines[i - 1][0][1]) > 1.4 * dist:
                    tmp = [(lines[i][0][0], lines[i][0][1] - dist), (lines[i][1][0], lines[i][1][1] - dist)]
                    lines.append(tmp)
                if board_img_height - lines[i][0][1] > dist:
                    tmp = None
                    if i == tmp_len - 1:
                        tmp = [(lines[i][0][0], lines[i][0][1] + dist), (lines[i][1][0], lines[i][1][1] + dist)]
                    elif lines[i + 1][0][1] - lines[i][0][1] > 1.4 * dist:
                        tmp = [(lines[i][0][0], lines[i][0][1] + dist), (lines[i][1][0], lines[i][1][1] + dist)]
                    if tmp is not None:
                        lines.append(tmp)

    def _lines_reconstruction(self, lines: [], dist, key):
        """"
        void method work on param: lines

        :param: lines lines: set of lines
        :param: dist -> value of distance between lines
        :param: key -> klucze - x to 0, y to 1
        """
        prev = -dist
        for i in range(len(lines)):
            tmp = None
            if lines[i][0][key] - prev > dist * 1.4:
                if key == 0:
                    tmp = [(lines[i][0][0] - dist, lines[i][0][1]), (lines[i][1][0] - dist, lines[i][1][1])]
                elif key == 1:
                    tmp = [(lines[i][0][0], lines[i][0][1] - dist), (lines[i][1][0], lines[i][1][1] - dist)]
                lines.append(tmp)
            prev = lines[i][0][key]

    def _find_corners_in_PIby2_1px_lines(self, line_image):
        """"
        a lot slower than goodFeatureToTrack() by opencv
        """
        corners = []
        gray = np.min(line_image)
        # print(gray)
        for i in range(1, len(line_image) - 1):
            for j in range(1, len(line_image[i]) - 1):
                # print(line_image[i - 1][j])
                if line_image[i - 1][j] == line_image[i + 1][j] == line_image[i][j + 1] == line_image[i][j - 1] == gray:
                    corners.append([i, j])

        return corners

    def _corners_logic(self, line_image):
        h8, width = line_image.shape[0], line_image.shape[1]
        white = np.zeros((h8, width, 3), np.uint8) + 255
        # cv2.imshow('lines', line_image)

        # white = cv2.cvtColor(line_image,cv2.COLOR_GRAY2BGR)
        corners = cv2.goodFeaturesToTrack(line_image, 0, 0.01, 10)
        corners: list = np.int0(corners)
        # corners = self._find_corners_in_PIby2_1px_lines(line_image)
        # sort with tolerance

        corners = sorted(corners, key=lambda x: (-x[0][0] // 4, -x[0][1] // 4))
        corners = np.reshape(corners, (-1, 18))

        rects = []
        for i in range(len(corners) - 1):
            line = []
            for j in range(0, len(corners[i]) - 2, 2):
                x1, y1 = corners[i][j], corners[i][j + 1]
                x2, y2 = corners[i + 1][j + 2], corners[i + 1][j + 3]
                line.append([(x1, y1), (x2, y2)])
            rects.append(line)
        for line in rects:
            for rect in line:
                cv2.rectangle(white, rect[0], rect[1],
                              [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)], thickness=-1)

        # cv2.imshow('cor', white)
        return rects

    def _show_fields(self, rects, cropped_image):
        cropped_image = cv2.cvtColor(cropped_image, cv2.COLOR_GRAY2BGR)
        tr = cropped_image.copy()

        for line in rects:
            for rect in line:
                cv2.rectangle(tr, rect[0], rect[1],
                              [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)], thickness=-1)
        # cor = rects[0][0]
        # print(cor)
        # cv2.rectangle(tr, cor[0], cor[1],
        #               [random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)], thickness=-1)
        opacity = 0.4
        cv2.addWeighted(tr, opacity, cropped_image, 1 - opacity, 0, cropped_image)
        for line in rects:
            for rect in line:
                org = (rect[1][1], rect[1][0] + 50)
                cv2.putText(cropped_image, rect[2], org, cv2.FONT_ITALIC, 1, [0, 0, 255], 2)

        cv2.imshow('fields', cropped_image)

    def _lines_logic(self, board_image):
        clache = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl_board = clache.apply(board_image)
        image = self.prepare(cl_board)
        h8, width = board_image.shape[0], board_image.shape[1]
        cdst = np.zeros((h8, width, 3), np.uint8) + 250
        # cdst = cv2.cvtColor(board_image, cv2.COLOR_GRAY2BGR)

        detected_lines = self._prepare_lines(image)
        print(detected_lines)
        poziome, pionowe = self._group_line(detected_lines)
        print(poziome)

        pionowe, dist_pion = self._filter_vertical_lines(pionowe, width)
        poziome, dist_poz = self._filter_horizontal_lines(poziome, h8)

        pionowe.sort(key=lambda x: x[0][0])
        poziome.sort(key=lambda x: x[0][1])
        # self._lines_reconstruction(pionowe, dist_pion, 0)
        # self._lines_reconstruction(poziome, dist_poz, 1)
        self._horizontal_lines_reconstruction(poziome, dist_poz, h8)
        self._vertical_lines_reconstruction(pionowe, dist_pion, width)

        for line in pionowe:
            cv2.line(cdst, line[0], line[1], (255, 0, 0), 1)
        for line in poziome:
            cv2.line(cdst, line[0], line[1], (255, 0, 0), 1)

        # cv2.imshow('line', cdst)
        return cdst

    def _find_A8_field(self, fields, clache_board_image):
        max_value = -1
        a8_cor = None
        a8_pic = None
        for i, j in zip([0, 0, 7, 7], [0, 7, 0, 7]):
            corner = fields[i][j]
            cr = clache_board_image[corner[1][1]:corner[0][1], corner[1][0]:corner[0][0]]
            blur = cv2.GaussianBlur(cr, (5, 5), 0)
            # mean = np.median(blur)
            variance = np.var(blur)
            print(i, j, variance)

            if variance > max_value:
                a8_cor = (i, j)
                max_value = variance
                a8_pic = cr

        cv2.imshow('a8', a8_pic)
        return a8_cor

    def _name_fields(self, fields, i, j):
        nums = [1, 2, 3, 4, 5, 6, 7, 8]

        letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
        first = None
        second = None

        if i == 0 and j == 0:
            letters = letters[::-1]
            # nums = nums[::-1]
        elif i == 0 and j == 7:
            letters = letters[::-1]
        print(i, j)
        # for n in range(len(nums)):
        #     for l in range(len(letters) - 1, -1, -1):
        #         signature = '' + str(letters[l]) + str(nums[n])
        #         fields[n][l].append(signature)
        x = 7
        for line in fields:
            y = 7
            for field in line:
                if i == j:
                    signature = '' + str(letters[y]) + str(nums[x])
                else:
                    signature = '' + str(letters[x]) + str(nums[y])
                field.append(signature)
                y -= 1
            x -= 1
        return fields

    def _fields_logic(self, fields, board_image):
        clache = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl_board = clache.apply(board_image)
        kernel = np.ones((5, 5), np.uint8)
        erosion = cv2.erode(cl_board, kernel, iterations=1)
        i, j = self._find_A8_field(fields, erosion)

        # h1_img = fields[i][j]
        # h1_img = cl_board[h1_img[1][1]:h1_img[0][1], h1_img[1][0]:h1_img[0][0]]
        # cv2.imshow('field', h1_img)
        named_fields = self._name_fields(fields, i, j)

        return named_fields

    def get_board(self, frame):
        prepare = self.prepare(frame)
        squares, _ = self._find_square(prepare)
        board = self._find_board(squares)
        cropp_to_board = self._crop_board(frame, board)
        return cropp_to_board

    def get_fields(self, board_image):
        chessboard_lines_img = self._lines_logic(board_image)
        chessboard_lines_img = cv2.cvtColor(chessboard_lines_img, cv2.COLOR_BGR2GRAY)
        fields = self._corners_logic(chessboard_lines_img)
        fields = self._fields_logic(fields, board_image)

        return fields


if __name__ == '__main__':
    d = Detector()
    image_ = cv2.imread('D:\Programming\python\chess-registrator\photos\moves\move_1.jpg', 0)
    # image_ = cv2.rotate(image_, cv2.ROTATE_90_CLOCKWISE)
    cv2.imshow('oryginal', image_)
    cropped = d.get_board(image_)
    cv2.imshow('crpped', cropped)

    fields = d.get_fields(cropped)

    d._show_fields(fields, cropped)
    cv2.waitKey()
