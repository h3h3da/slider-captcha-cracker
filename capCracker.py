from PIL import Image
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
import cv2
import numpy as np
from io import BytesIO
import time, requests


class CrackSlider():
    """
    通过浏览器截图，识别验证码中缺口位置，获取需要滑动距离，并模仿人类行为破解滑动验证码
    这里使用网易易盾滑动模块http://dun.163.com/trial/jigsaw
    过程参考https://www.jianshu.com/p/f12679a63b8d
    目前进度：已完成本地测试，代码待优化。
    """
    def __init__(self):
        self.url = 'http://dun.163.com/trial/jigsaw'
        chromedriver = "C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe" # 先获取程序控制Chrome，这里使用selenium+Chromedriver，可参考https://ccie.lol/knowledge-base/python-control-chrome/
        self.driver = webdriver.Chrome(chromedriver)
        self.wait = WebDriverWait(self.driver, 20) #等待页面元素的加载
        self.zoom = 1
    
    # 打开网址
    def open(self):
        self.driver.get(self.url)

    def get_pic(self):
        target = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'yidun_bg-img'))) # 背景图片
        template = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'yidun_jigsaw'))) # 滑动图片
        target_link = target.get_attribute('src')
        template_link = template.get_attribute('src')
        target_img = Image.open(BytesIO(requests.get(target_link).content))
        template_img = Image.open(BytesIO(requests.get(template_link).content))
        target_img.save('target.jpg')
        template_img.save('template.png')
        local_img = Image.open('target.jpg')
        size_loc = local_img.size

        self.zoom = 320 / int(size_loc[0])
    
    # 参数：要移动的总距离
    def get_tracks(self, distance) -> dict:
        print(distance)
        
        v = 0
        t = 0.5
        forward_tracks = []
        current = 0
        mid = distance * 3 / 5  #减速阀值

        while current < distance:
            # 3/5 的加速带和 2/5 的减速带，为了使最后的距离为distance，加速度的比值为2：3
            if current < mid:
                a = 200  #加速度为200
            else:
                a = -300  #加速度-300
            
            s  = v * t + 0.5 * a * (t ** 2)
            v = v + a * t
            current += s
            forward_tracks.append(s)
        if current > distance:
            forward_tracks.append(distance - current)
        # 添加一个自适应值10，效果比较好
        forward_tracks.append(10)    
        # 去除最开始的20
        back_tracks = [-10, -5, -3, -2]   
        return {'forward_tracks': forward_tracks, 'back_tracks': back_tracks}

    def match(self, target, template) -> int:
        img_rgb = cv2.imread(target) # 默认读取彩色图像，不包括透明度
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY) # 转换为灰度图
        template = cv2.imread(template, 0) # 滑动图片转换为黑白
        # 得到滑动图片的高和宽
        w, h = template.shape[::-1]
        print(w, h)

        res = cv2.matchTemplate(img_gray, template, cv2.TM_CCOEFF_NORMED)
        run = 1

        # 使用二分法查找阈值的精确值
        L = 0
        R = 1
        while run < 20:
            run += 1
            threshold = (R + L) / 2
            print(threshold)
            if threshold < 0:
                print('Error')
                return None
            loc = np.where(res >= threshold)
            print(len(loc[1]))
            # 如果当前阈值查找结果数量大于1，则说明阈值太小，需要往右端靠近，即左端就增大，即L += (R - L) / 2
            if len(loc[1]) > 1:
                L += (R - L) / 2
            elif len(loc[1]) == 1:
                print('目标区域起点x坐标为：%d' % loc[1][0])
                break
            # 如果结果数量为0，则说明阈值太大，右端应该减小，即R -= (R - L) / 2
            elif len(loc[1]) < 1:
                R -= (R - L) / 2
        return loc[1][0]

    def crack_slider(self):
        slider = self.wait.until(EC.element_to_be_clickable((By.CLASS_NAME, 'yidun_slider')))
        ActionChains(self.driver).click_and_hold(slider).perform()
        # 前进
        for track in tracks['forward_tracks']:
            ActionChains(self.driver).move_by_offset(xoffset=track, yoffset=0).perform()
        # 停顿0.1 秒
        time.sleep(0.1)
        # 在最终位置进行微小距离的来回移动，模拟真人的轨迹
        ActionChains(self.driver).move_by_offset(xoffset=-4, yoffset=0).perform()
        ActionChains(self.driver).move_by_offset(xoffset=4, yoffset=0).perform()
        # 为了更好的模拟真人，适当的增加停顿时间
        time.sleep(0.1)
        # 释放滑块
        ActionChains(self.driver).release().perform()


if __name__ == '__main__':
    cs = CrackSlider()
    
    # 打开链接
    cs.open()
    target = 'target.jpg' # 背景图片
    template = 'template.png' # 滑动图片
    # 得到图像以及缩放比
    cs.get_pic()
    # 得到缺块的位置
    distance = cs.match(target, template)

    tracks = cs.get_tracks(distance * cs.zoom)  # 对位移的缩放计算
    cs.crack_slider()