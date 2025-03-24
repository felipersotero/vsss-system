import cv2
import numpy as np
import threading
import time
import os

class CUDAPipeline:
    def __init__(self, image_path):
        if not os.path.exists(image_path):
            raise ValueError("Image path does not exist.")
        
        self.image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if self.image is None:
            raise ValueError("Image not found or unable to load.")
        
        self.cuda_image = cv2.cuda_GpuMat()
        self.cuda_image.upload(self.image)
        
        self.intermediate_image1 = cv2.cuda_GpuMat()
        self.intermediate_image2 = cv2.cuda_GpuMat()
        self.intermediate_image3 = cv2.cuda_GpuMat()
        self.result_image = cv2.cuda_GpuMat()
    
    def time_stage(self, stage_function, stage_name):
        start_time = time.time()
        stage_function()
        end_time = time.time()
        print(f"{stage_name} took {end_time - start_time:.4f} seconds")
    
    def stage1(self):
        cv2.cuda.cvtColor(self.cuda_image, cv2.COLOR_GRAY2BGR, self.intermediate_image1)
    
    def stage2(self):
        gaussian_blur = cv2.cuda.createGaussianFilter(cv2.CV_8UC3, cv2.CV_8UC3, (5, 5), 0)
        gaussian_blur.apply(self.intermediate_image1, self.intermediate_image2)
    
    def stage3(self):
        canny_edge = cv2.cuda.createCannyEdgeDetector(100, 200)
        canny_edge.detect(self.intermediate_image2, self.result_image)
    
    def stage4(self):
        sobel_filter = cv2.cuda.createSobelFilter(cv2.CV_8UC1, cv2.CV_8UC1, 1, 0, ksize=3)
        sobel_filter.apply(self.result_image, self.intermediate_image3)

def main():
    image_path = 'C:\Users\saulo\Desktop\vsss-system\src\data\tests\img.png'  # Atualize com o caminho correto para sua imagem
    pipeline = CUDAPipeline(image_path)
    
    threads = [
        threading.Thread(target=pipeline.time_stage, args=(pipeline.stage1, "Stage 1")),
        threading.Thread(target=pipeline.time_stage, args=(pipeline.stage2, "Stage 2")),
        threading.Thread(target=pipeline.time_stage, args=(pipeline.stage3, "Stage 3")),
        threading.Thread(target=pipeline.time_stage, args=(pipeline.stage4, "Stage 4"))
    ]
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    result = pipeline.intermediate_image3.download()
    cv2.imshow('Result', result)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
