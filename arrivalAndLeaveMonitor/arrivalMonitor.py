#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
**********************************************************************
This moudle can monitor arrival list 
and when a new car arrivaes,it pops up a Dialog window
**********************************************************************

version:1.1.0  新增监控与v6相结合
                add V6 obj in ArrivalMonitor class
----------------------------------------------------------------------               
version:1.1.1  实际到车监控会在启动时先获取一次
---------------------------------------------------------------------- 

author:dingjian
last date:2019-1-11 10:53
version:1.1.1
'''
import sys
sys.path.append("..")
from yunli import yunli
from v6web import v6web
import tkinter as tk
import tkinter.messagebox as messagebox
import time
import json
import threading



def getArrivalInfoByRecordList(recordList,center):
    '''
    '从考勤记录中获取到达信息  '
    '如果福牛或者分拨打卡  返回(True,scanTime)'
    '如果没有进港  返回(False,None)'
    recordList  考勤记录
    center    本站
    return  (True,eachRecord)  or (False,None)
    '''
    if center is not None:
        if '集配站' in center:
            center = center
        elif '分拨' in center:
            center = center
        else:
            center += '分拨'
    else:
        print('getArrivalInfoByRecordList center error')
        raise Exception('can not be None')
    
    if recordList is not None:
        if len(recordList) != 0:
            for eachRecord in recordList:
                if eachRecord['inout'] == 'IN' and (eachRecord['scanType'] == 'DRIVER_PLATFORM' or eachRecord['scanType'] == 'CLIENT') and eachRecord['nodeName'] == center:
                    return (True,eachRecord)
            return (False,None)
        else:
            print('getArrivalInfoByRecordList recordList no record')
            return (False,None)
    else:
        print('getArrivalInfoByRecordList recordList is None')
        raise Exception('can not be None')

def extractListFromPlanArrivalList(arrivalList):
    '''
    '从计划进港列表中  提取未进港的信息'
    arrivalList  计划进港列表
    return []   计划进港中未进港列表
    '''
    returnList = []
    if arrivalList is not None:
        for each in arrivalList:
            jsonEach = json.loads(each)
            eachList = jsonEach['pageList']['list']
            for item in eachList:
                #removeAlreadyArrivalFromList
                if item['type'] == '未到达':
                    returnList.append(item)
        return returnList
    else:
        print('extractListFromPlanArrivalList fail')
        return None
    
    

def extractListFromActualArrivalList(arrivalList):
    '''
    extract List From Actual Arrival List
    accept ['{"success":true,"pageList":{"list":[{"id":7784845,"lockVersion":0,"jobId":3906816,"nodeId":290501,
    return a list like [{},{},{}...]
    ['{"success":true,"pageList":{"l...]  ==>  [{},{},{}...]
    '从响应列表中提取一个列表'
    return []  实际到达列表
    '''
    returnList = []
    if arrivalList is not None:
        for each in arrivalList:
            jsonEach = json.loads(each)
            eachList = jsonEach['pageList']['list']
            for item in eachList:
                returnList.append(item)
        return returnList
    else:
        print('extractListFromActualArrivalList fail')
        return None

def isItemInArrivalList(item,ArrivalList):
    '''
    '判断item是否在ArrivalList中'
    return True or False
    '''
    if item is None or ArrivalList is None:
        raise Exception('can not be None')
    
    if len(ArrivalList) == 0:
        return False
    
    for each in ArrivalList:
        '''
        if each['jobCode'] == item['jobCode'] and str(each['scanTime']) == str(item['scanTime']):
            return True
        '''
        #只判断任务单号
        if each['jobCode'] == item['jobCode'] :
            return True
    return False

'''
def popWindow():
    def return_callback(event):
        print('quit...')
        print(entry.get())
        root.quit()
    def close_callback():
        print('message', 'no click...')
        root.quit()
    root = tkinter.Tk(className='title')
    root.wm_attributes('-topmost', 1)
    screenwidth, screenheight = root.maxsize()
    width = 300
    height = 100
    size = '%dx%d+%d+%d' % (width, height, (screenwidth - width)/2, (screenheight - height)/2)
    root.geometry(size)
    root.resizable(0, 0)
    lable = tkinter.Label(root, height=2)
    lable['text'] = 'message'
    lable.pack()
    entry = tkinter.Entry(root)
    entry.bind('<Return>', return_callback)
    entry.pack()
    btn = tkinter.Button(root)
    
    btn.pack()
    entry.focus_set()
    root.protocol("WM_DELETE_WINDOW", close_callback)
    root.mainloop()
    str = entry.get()
    root.destroy()
'''

class ArrivalMonitor:
    '''
    main class
    '''
    #监控的分拨
    center = None
    #ArrivalMonitor类中的Yunli对象
    yunli = None
    #开始监控的时间，在startMonitor()中被赋值，只在类实例化并开始监控时赋值一次
    firstStartMonitorTimeLong = None
    #是否启动实际到达监控
    isMonitorWithActualArrivalList = False
    #是否启动计划到达监控
    isMonitorWithPlanArrivalList = False
    #初始到达列表
    firstStartArrivalList = None
    #用于分派工单的v6web
    v6 = None
    
    def __init__(self,center=None,mYunli=None,mV6=None,userName=None,psw=None):
        '''
        __init__()初始化函数
        '初始化ArrivalMonitor中的yunli'
        '如果传参为空，则自己实例化'
        center     监控的分拨 
        mYunli     传参的yunli对象   如果传参为空，则自己实例化
        mV6         用于分派工单的v6web
        userName   运力的userName
        psw        运力的psw
        '''
        if center is not None:
            self.center = center
        
        if mYunli is None:
            self.yunli = yunli.Yunli(userName,psw)
            self.yunli.login()
            if self.yunli.testIfLogin() == True:
                print('New Yunli success')
        elif mYunli is not None:
            self.yunli = mYunli
            
            if self.yunli.testIfLogin() == False:
                self.yunli.login()
            else:
                print('Parameter Yunli success')
        
        if mV6 is None:
            self.v6 = v6web.V6()
            self.v6.loginWithWindow()
            if self.v6.testIfLogin():
                if self.v6.workTeamList == None:
                    print('获取班组中...')
                    self.v6.workTeamList = self.v6.getCenterWorkTeam()
                    if self.v6.workTeamList is not None:
                        print('共获取%d个班组'%len(self.v6.workTeamList))
                        self.center = self.v6.centerName
                    else:
                        print('获取班组失败...')
                        self.v6 = None
            else:
                print('获取班组失败...')
                self.v6 = None
            
        else:
            self.v6 = mV6
            self.v6.loginWithWindow()
            if self.v6.workTeamList == None:
                print('获取班组中...')
                self.v6.workTeamList = self.v6.getCenterWorkTeam()
                if self.v6.workTeamList is not None:
                    print('共获取%d个班组'%len(self.v6.workTeamList))
                    self.center = self.v6.centerName
                else:
                    print('获取班组失败...')
                    self.v6 = None
    
    def monitor(self,dataList=None): 
        '''
        not ok
        '''
        if dataList is not None:
            self.firstStartArrivalList=extractListFromActualArrivalList(dataList)
            nowArrivalList = []
            nowArrivalList = extractListFromActualArrivalList(self.yunli.getActualArrivalList(thisCenter=self.center,actualTimeBegin=self.firstStartMonitorTimeLong,actualTimeEnd=None))
            #print(nowArrivalList)
            if nowArrivalList is not None and self.firstStartArrivalList is not None:
                for each in nowArrivalList:
                    if isItemInArrivalList(each, self.firstStartArrivalList) == False:
                        
                        #print(each)
                        t = threading.Thread(target=self.popWindow)
                        t.start()
                        time.sleep(delay)
        else:
            
            pass   
    
    def startMonitorWithActualArrivalList(self,delaySecond=None,updatePeriodMinute=None):
        '''
        ArrivalMonitor With ActualArrivalList main loop
        delaySecond  刷新间隔
        updatePeriodMinute  系统更新状态间隔
        '由于调度系统的列表是整点刷新，0或5分钟整点刷新，因此整点时才监控'
        '实际到达列表监控主循环'
        '''
        if delaySecond is None:
            delaySecond = 20
            
        if updatePeriodMinute is None:
            updatePeriodMinute = 1
        
        #初始化开始时间
        if self.firstStartMonitorTimeLong is None:
            self.firstStartMonitorTimeLong = int(yunli.getCurrentLongTime())
        #初始化列表
        if self.firstStartArrivalList is None:
            self.firstStartArrivalList=extractListFromActualArrivalList(self.yunli.getActualArrivalList(thisCenter=self.center,actualTimeBegin=self.firstStartMonitorTimeLong-5*60*1000,actualTimeEnd=None))  
            #print(self.firstStartArrivalList)
        
        self.isMonitorWithActualArrivalList = True
        print("start monitor with ActualArrivalList... ")
        #第一次启动自己开始获取一次
        nowArrivalList = extractListFromActualArrivalList(self.yunli.getActualArrivalList(thisCenter=self.center,actualTimeBegin=None,actualTimeEnd=None))
        if nowArrivalList is not None and self.firstStartArrivalList is not None:
            for each in nowArrivalList:
                if isItemInArrivalList(each, self.firstStartArrivalList) == False:
                    self.firstStartArrivalList.append(each)
                    task = threading.Thread(target=self.popWindow,args=(each,None))
                    task.start()
                    time.sleep(1)
        #获取完后，开始主循环        
        while self.isMonitorWithActualArrivalList == True:
            nowArrivalList = None
            nowTimeLong = int(yunli.getCurrentLongTime())
            nowTimeStr = yunli.parseLongTimeToDateString(nowTimeLong)
            nowMinute = int(nowTimeStr.split(":")[1])
            #print(nowTimeStr)
            if nowMinute % updatePeriodMinute == 0:
                #print("geting....")
                nowArrivalList = extractListFromActualArrivalList(self.yunli.getActualArrivalList(thisCenter=self.center,actualTimeBegin=None,actualTimeEnd=None))
                if nowArrivalList is not None and self.firstStartArrivalList is not None:
                    for each in nowArrivalList:
                        if isItemInArrivalList(each, self.firstStartArrivalList) == False:
                            #print(each)
                            self.firstStartArrivalList.append(each)
                            task = threading.Thread(target=self.popWindow,args=(each,None))
                            task.start()
                            time.sleep(1)
                            
                else:
                    print("start monitor with ActualArrivalList fail")
                    print("reStart")
                    self.startMonitorWithActualArrivalList(delaySecond=delaySecond,updatePeriodMinute=updatePeriodMinute)
                time.sleep(delaySecond)
            else:
                time.sleep(delaySecond)
    
    def startMonitorWithPlanArrivalList(self,delaySecond=None):
        '''
        ArrivalMonitor With ActualPlanList main loop
        delaySecond  刷新间隔
        '计划到达列表监控主循环'
        '''
        if delaySecond is None:
            delaySecond = 5
            
        #初始化列表
        if self.firstStartArrivalList is None:
            self.firstStartArrivalList = []
            
        self.isMonitorWithPlanArrivalList = True
        print("start monitor with PlanArrivalList... ")
        while self.isMonitorWithPlanArrivalList == True:
            #取得未到达计划列表
            planList=extractListFromPlanArrivalList(self.yunli.getPlanArrivalList(thisCenter=self.center,planArrTimeBegin=None,planArrTimeEnd=None))  
            #print(planList)
            #print(len(planList))
            if planList is not None:
                for each in planList:
                    task = threading.Thread(target=self.popWindowIfArrival,args=(each,))
                    task.start()
            
            time.sleep(delaySecond)
     
    def startMonitor(self,ActualDelay=None,ActualUpdatePeriod=None,planDelay=None):
        t1 = threading.Thread(target=monitor.startMonitorWithActualArrivalList,args=(ActualDelay,ActualUpdatePeriod))
        t2 = threading.Thread(target=monitor.startMonitorWithPlanArrivalList,args=(planDelay,))
        t1.start()
        t2.start()
            
    def stopMonitor(self):
        print("stop monitor")
        self.isMonitorWithActualArrivalList = False
        self.isMonitorWithPlanArrivalList = False
        
        
    
    def popWindow(self,eachInfo,scanTime=None):
        '''
        eachInfo  需要弹框提示的任务原始信息
        scanTime  实际进港扫描时间  如果为None 则在eachInfo中获取
        '显示提示框'
        '''
        #print('popWindow start')
        app = tk.Tk()
        app.wm_attributes('-topmost', 1)
        screenwidth, screenheight = app.maxsize()
        width = 300
        height = 250
        size = '%dx%d+%d+%d' % (width, height, (screenwidth - width)/2, (screenheight - height)/2)
        app.geometry(size)
        app.resizable(width=False, height=False)
        app.title("到达预警")
        
        def buttonCallBack():
            stringInEntry = entry.get()
            if stringInEntry == '':
                app.destroy()
                return
            scanCode = eachInfo['pinCode']
            workTeamCode = stringInEntry
            
            if self.v6.assignUnloadTaskByScanCode(scanCode,workTeamCode):
                messagebox.showinfo('提示', '分派成功')
                #self.popMessageBox('提示', '分派成功')
                #win32api.MessageBox(0, "分派成功", "提示",win32con.MB_OK)
                
                app.destroy()
                #print('分派成功')
            else:
                messagebox.showinfo('提示', '分派失败')
                #win32api.MessageBox(0, "分派失败", "提示",win32con.MB_OK)
                #handle = win32gui.FindWindow("提示", None) 
                #print(handle)
                #win32gui.SetForegroundWindow (handle)
                #win32gui.SetWindowPos(handle, win32con.HWND_TOPMOST, 0,0,0,0, win32con.SWP_NOMOVE | win32con.SWP_NOACTIVATE| win32con.SWP_NOOWNERZORDER|win32con.SWP_SHOWWINDOW)
                #popMessageBox('提示', '分派失败')
                app.destroy()
                time.sleep(0.5)
                if eachInfo['type'] == '未到达':
                    self.popWindow(eachInfo, scanTime=None)
                else:
                    self.popWindow(eachInfo, scanTime)
                #self.popWindowIfArrival(eachItem)
                #print('分派失败')
            
            
        
        def entryReturnCallBack(event):
            buttonCallBack()
        
        label = tk.Label(app,text=eachInfo['laneName']+'到了',font=('黑体',16),pady=20)
        label.pack()
        
        scanTimeStr = ''
        if scanTime is not None:
            scanTimeStr = yunli.parseLongTimeToDateString(int(scanTime))
        else:
            scanTimeStr = yunli.parseLongTimeToDateString(int(eachInfo['scanTime']))
        textStr = '车线:'+eachInfo['laneName']+'\n'\
                    +'任务单：'+eachInfo['jobCode']+'\n'\
                    +'考勤码：'+eachInfo['pinCode']+'\n'\
                    +'车牌：'+eachInfo['licensePlate']+'  ' + yunli.getValueInDic(eachInfo,'trailerLicensePlate')+'\n'\
                    +'打卡时间：'+scanTimeStr
        text = tk.Text(app,font=('宋体',10),height=6)
        
        text.insert(tk.INSERT, textStr)
        text.config(state=tk.DISABLED)
        text.pack()
        
        frame = tk.Frame(app)
        label2 = tk.Label(frame,text="分派卸车工单：")
        label2.pack(side=tk.LEFT)
        entry = tk.Entry(frame)
        entry.bind('<Return>', entryReturnCallBack)
        entry.pack(side=tk.RIGHT)
        frame.pack(pady=20)
        
        button = tk.Button(app,text='确定',font=('黑体',14),command=buttonCallBack)
        button.pack()
       
        app.mainloop()
        
    def popWindowIfArrival(self,eachItem):
        '''
        eachItem  计划但还未进港的任务
        '计划进港列表中   未进港的任务   如果检查到在本站有福牛打卡或者分拨打卡记录，则弹框提醒'
        '''
        jobCode = eachItem['jobCode']
        recordList = self.yunli.getClientBarCodeRecordListByJobCode(jobCode)
        arrivalInfo = getArrivalInfoByRecordList(recordList,self.center)
        if arrivalInfo[0]:
            eachItem['scanTime'] = arrivalInfo[1]['scanTime']
        if arrivalInfo[0] == True and isItemInArrivalList(eachItem, self.firstStartArrivalList) == False:
            #print(recordList)
            self.firstStartArrivalList.append(eachItem)
            self.popWindow(eachItem,arrivalInfo[1]['scanTime'])
            
        
        
        

if __name__ == "__main__":
    #popWindow()
    
    monitor = ArrivalMonitor(center=None,userName='BG269073',psw='123456789Mm')
    #monitor.startMonitorWithActualArrivalList(delaySecond=3,updatePeriodMinute=1)
    '''
    t1 = threading.Thread(target=monitor.startMonitorWithPlanArrivalList)
    t2 = threading.Thread(target=monitor.startMonitorWithActualArrivalList)
    t1.start()
    t2.start()
    '''
    if monitor.v6 is not None:
        t = threading.Thread(target=monitor.startMonitor)
        t.start()
    