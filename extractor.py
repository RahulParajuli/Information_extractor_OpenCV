import cv2
import numpy as np
import pytesseract
from pytesseract import Output
from pdf2image import convert_from_path
import re
import json

def get_ocr_result(image1):
    """
    input parameter: image
    output: dictionary of ocr results
    """
    ret,thresh_value = cv2.threshold(image1,180,255,cv2.THRESH_BINARY_INV)
    kernel = np.ones((5,5),np.uint8)
    dilated_value = cv2.dilate(thresh_value,kernel,iterations = 1)
    contours, hierarchy = cv2.findContours(dilated_value,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    
    cordinates = []
    result = {}
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        cordinates.append((x,y,w,h))
        #bounding the images
        if h > 60 and w < 1300:
            cv2.rectangle(image,(x,y),(x+w,y+h),(0,0,255),1)
            #extracting the ROI
            ROI1 = image[y:y+h,x:x+w]
            # cv2.imwrite('ROI_{}.png'.format(x),ROI)
            #extracting the text from the ROI
            data = pytesseract.image_to_string(ROI1, lang='eng',config='--psm 6', output_type=Output.DICT)
            splitted_data = data['text'].splitlines()
            try:
                key = splitted_data[0]
                value = splitted_data[1:]
                if value == []:
                    value = "None"
                elif key == "Vessel/Voyage":
                    value1 = str(splitted_data[1].split(" ")[0:3]).replace("[", "").replace("]", "").replace("'", "")
                    value2 = splitted_data[1].split(" ")[-1]
                    final_res['vessel_name'] = value1
                    final_res['voyage_num'] = value2
                else:
                    value.pop()
            except:
                pass
            result[key] = value
    return result

#since some contents are not extracted properly, we need to extract them manually using regex
def regex_search(image1):
    """
    input parameter: image
    output: dictionary of regex search results
    """

    cordinates = []
    #slicing of image in focus to non ocr detected text
    height, width = image1.shape[:2]
    halfwidth = width/2
    halfheight = height/2
    im2 = image1[int(halfheight/2)+230:int(halfheight)-310, int(halfwidth)-180:int(width)]

    #extraction from designated part of invoice
    ret,thresh_value = cv2.threshold(im2,180,255,cv2.THRESH_BINARY_INV)
    kernel = np.ones((5,5),np.uint8)
    dilated_value = cv2.dilate(thresh_value,kernel,iterations = 1)

    contours, hierarchy = cv2.findContours(dilated_value,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        x,y,w,h = cv2.boundingRect(cnt)
        cordinates.append((x,y,w,h))
        
        #bounding the images
        if h> 100 and w > 200:
            cv2.rectangle(im2,(x,y),(x+w,y+h),(0,255,0),3)
            #extracting the ROI
            ROI1 = im2[y:y+h,x:x+w]
           #extracting the text from the ROI
            data = pytesseract.image_to_string(ROI1, lang='eng',config='--psm 6', output_type=Output.DICT)
            a = data["text"].replace("\n", "")

            pattern_HBL = "B\/L[a-z\d]+ *[a-z\d]+"
            match_HBL = re.search(pattern_HBL, a, flags= re.IGNORECASE)
            matched_HBL = match_HBL.group(0).split(" ")[0]

            pattern_MBL = "B\/L[a-z\d]+ *[a-z\d]+"
            match_MBL = re.search(pattern_MBL, a, flags= re.IGNORECASE)
            matched_MBL = match_MBL.group(0).split(" ")[1]

            pattern_SCAC_MBL = "\| *[a-z]+ *[a-z]+"
            match_SCAC_MBL = re.search(pattern_SCAC_MBL, a, flags= re.IGNORECASE)
            matched_SCAC_MBL = match_SCAC_MBL.group(0).split(" ")[1]

            pattern_SCAC_HBL = "code \| *([a-z]+)"
            match_SCAC_HBL = re.search(pattern_SCAC_HBL, a, flags= re.IGNORECASE)
            matched_SCAC_HBL = match_SCAC_HBL.group(0).split(" ")[1]

            final_res["hbl_num"] = matched_HBL
            final_res["mbl_num"] = matched_MBL
            final_res['mbl_scac'] = matched_SCAC_MBL
            final_res['hbl_scac'] = matched_SCAC_HBL

    cv2.imwrite('files/nonOCRdetected/HBLandMBL.png',im2)
    return final_res
    
        
if __name__ == "__main__":
    """
    input parameter: pdf file
    output: json file
    """ 

    file = input("enter a file path of pdf file or press 'Enter' to use sample pdf: ")
    #converting pdf to image
    try:
        if file.endswith(".pdf"):
            pages = convert_from_path(file, dpi=300)
            print("\nYou have entered a pdf file")
            print("Converting pdf for operation\n"+ "please wait...\n"+ "_"*50)
            for page in pages:
                page.save("files/pdfconverted/page.jpg", 'JPEG')

        print("Hold still! The data from sample is being extracted\n"+ "-"*50)
    except:
        print("Error in getting the document\nTrying from sample document")

    file_path = "files/pdfconverted/"
    file =  file_path+r'page.jpg'

    image1 = cv2.imread(file, 0)
    image = cv2.imread(file)
    
    keys_dict = {
                "1. Seller Name & Address": "seller",
                "2.Buyer Name & Address(Importer of Record)":"buyer",
                "Container": "container",
                "POL": "pol",
                "POD": "pod",
                "ETA of POD": "eta",
                "ETD of POL":"etd",
                "Vessel_voyage": "voyage_num",
                "Regular or Straight B/L": "mbl_num",
                "SCAC code": "mbl_scac",
                "HB/L#":"hbl_num",
                "SCAC": "hbl_scac",
                "Type of movement": "type_of_movement"
                }
    final_res = {}

    result = get_ocr_result(image1)
    for key,value in keys_dict.items():
        if key in result:
            final_res[value] = str(result[key]).replace("[","").replace("]","").replace(",", "").replace("'","")
        else:
            regex_search(image1)

    print(final_res)
    json.dump(final_res, open("result.json", "w"))
    print("_"*50 + "\njson file created successfully")
    cv2.imwrite('files/OCRdetected/detectable.jpg',image)
