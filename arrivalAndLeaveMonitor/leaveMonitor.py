#!/usr/bin/env python
# -*- coding:utf-8 -*-

'''
**********************************************************************
This moudle can monitor leave list 
and when a new car leave,it pops up a Dialog window
**********************************************************************

version:1.0.3
    add  getSendLoadWeightListByJobCode(self,jobCode) 查询任务单装载情况
    in LeaveMonitor class
----------------------------------------------------------------------
version:1.0.4
    add  startMonitorWithEarlyWarning(self,earlyMinutes=None,delaySecond=None) 提前预警
    in LeaveMonitor class
----------------------------------------------------------------------
version:1.0.5
    add  出发窗口现在可以备注任务单
----------------------------------------------------------------------

author:dingjian
last date:2019-1-15 1:08
version:1.0.5
'''
import sys
sys.path.append("..")
from yunli import yunli
from fuxi import fuxi
import tkinter as tk
import tkinter.messagebox as messagebox
import time
import json
import threading
import pickle as pk


def loadPklFile(filename):
    '''
    load .pkl file into obj
    '''
    try:
        file = open(filename,'rb')
        obj = pk.load(file)
        file.close()
        if obj != None:
            return obj
    except:
        return None
    
def pickleToFile(obj,filename):
    '''
    pickle obj to file
    '''
    if obj != None:
        file = open(filename,'wb')    
        pk.dump(obj,file)
        file.close()

def sumAllLoadWeightFromWeightInfoList(lst):
    '''
    build in function
    '从装载信息列表中求装载之和
    accept [('南京',3052.36),('苏州',7052.36)...]
    return float
    [('南京',3052.36),('苏州',7052.36)...]  ==>  10104.72
    '''
    if lst ==None:
        return 0
    if len(lst)==0:
        return 0
    allWeight = 0
    for each in lst:
        allWeight += float(each[1])
    return allWeight

def extractListFromPlanLeaveList(leaveList):
    '''
    build in function
    '从计划出港列表中  提取未出港的信息列表'
    leaveList  计划出港列表
    return []   计划进港中未出港列表
    '''
    returnList = []
    if leaveList is not None:
        for each in leaveList:
            jsonEach = json.loads(each)
            eachList = jsonEach['pageList']['list']
            for item in eachList:
                #removeAlreadyArrivalFromList
                if 'actualTime' not in item.keys():
                    returnList.append(item)
        return returnList
    else:
        print('extractListFromPlanArrivalList fail')
        return None

def extractListFromActualLeaveList(leaveList):
    '''
    build in function
    extract List From Actual Arrival List
    accept ['{"success":true,"pageList":{"list":[{"id":7784845,"lockVersion":0,"jobId":3906816,"nodeId":290501,
    return a list like [{},{},{}...]
    ['{"success":true,"pageList":{"l...]  ==>  [{},{},{}...]
    '从响应列表中提取一个列表'
    return []  实际到达列表
    '''
    returnList = []
    if leaveList is not None:
        for each in leaveList:
            jsonEach = json.loads(each)
            eachList = jsonEach['pageList']['list']
            for item in eachList:
                returnList.append(item)
        return returnList
    else:
        print('extractListFromActualArrivalList fail')
        return None

def isItemInLeaveList(item,leaveList):
    '''
    build in function
    '判断item是否在LeaveList中'
    return True or False
    '''
    if item is None or leaveList is None:
        raise Exception('can not be None')
    
    if len(leaveList) == 0:
        return False
    
    for each in leaveList:
        '''
        if each['jobCode'] == item['jobCode'] and str(each['scanTime']) == str(item['scanTime']):
            return True
        '''
        #只判断任务单号
        if each['jobCode'] == item['jobCode'] :
            return True
    return False

def ifArrivalInCenterByRecordList(recordList,center):
    '''
    '是否在本站有到达考勤
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
        print('LeaveMonitor ifArrivalInCenterByRecordList center error')
        raise Exception('can not be None')
    
    if recordList is not None:
        if len(recordList) != 0:
            for eachRecord in recordList:
                if eachRecord['inout'] == 'IN' and (eachRecord['scanType'] == 'DRIVER_PLATFORM' or eachRecord['scanType'] == 'CLIENT')  and eachRecord['nodeName'] == center:
                    return (True,eachRecord)
            return (False,None)
        else:
            return (False,None)
    else:
        print('LeaveMonitor ifArrivalInCenterByRecordList recordList is None')
        raise Exception('can not be None')
    

def getLeaveInfoByRecordList(recordList,center):
    '''
    '从考勤记录中获取出发信息  '
    '如果福牛或者分拨打卡  返回(True,scanTime)'
    '如果没有出港  返回(False,None)'
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
                #if eachRecord['inout'] == 'OUT' and (eachRecord['scanType'] == 'DRIVER_PLATFORM' or eachRecord['scanType'] == 'CLIENT')  and eachRecord['nodeName'] == center:
                if eachRecord['inout'] == 'OUT' and eachRecord['scanType'] == 'DRIVER_PLATFORM'  and eachRecord['nodeName'] == center:
                    return (True,eachRecord)
            return (False,None)
        else:
            return (False,None)
    else:
        print('LeaveMonitor getLeaveInfoByRecordList recordList is None')
        raise Exception('can not be None')

class LeaveMonitor:
    '''
    main class
    '''
    #监控的分拨
    center = None
    #LeaveMonitor类中的Yunli对象
    yunli = None
    #LeaveMonitor中的fuxi对象
    fuxi = None
    #yunli的username
    username = None
    #yunli的password
    password = None
    #已经出发的列表
    firstStartLeaveList = None
    #开启监控的初始时间，只初始化一次
    firstStartMonitorTimeLong = None
    #是否启动实际车发监控
    isMonitorWithActualLeaveList = False
    #是否启动计划车发监控
    isMonitorWithPlanLeaveList = False
    #是否启动发车前实时监控监控
    isMonitorWithEarlyWarning = False
    #已经显示发车前预警对话框的列表
    alreadlyPopEarlyWarningList = []
    
    
    def __init__(self,center=None,mYunli=None,mFuxi=None,username=None,password=None):
        '''
        center     监控的分拨 
        mYunli     传参的yunli对象   如果传参为空，则自己实例化
        mFuxi      传参的fuxi对象   如果传参为空，则自己实例化
        userName   运力的userName
        password        运力的psw
        '''

        if center ==None and mYunli==None and mYunli==None and username==None and password==None:
            #载入之前的登录信息
            self.loadLoginInfo()
            self.loginWithWindow()
            if self.center !=None and self.username!=None and self.password!=None and self.yunli!=None and self.fuxi!=None:
                if self.yunli.testIfLogin() and fuxi.testIfLogin(self.fuxi.opener,self.fuxi.username)[0]:
                    print('Load login info success')
                    return

        
        if center != None:
            self.center = center

        if mYunli != None:
            self.yunli = mYunli
            try:
                #传入的yunli对象  可以登录  说明传入的是Yunli()  Yunli().login()
                if self.yunli.testIfLogin() == False:
                    self.yunli.loginWithWindow()
                else:
                    print('Parameter Yunli success')
                    self.username = self.yunli.username
                    self.password = self.yunli.psw_original
            except:
                #传入的yunli对象  无法登陆  说明传入的是Yunli()  没有 Yunli().login()
                self.yunli.loginWithWindow()
                if self.yunli.testIfLogin() == False:
                    self.yunli.loginWithWindow()
                else:
                    print('Parameter Yunli success')
                    self.username = self.yunli.username
                    self.password = self.yunli.psw_original
        #外部没有传入Yunli对象 自己创建
        else:
            #如果传入了用户名密码
            if username !=None and password !=None:
                self.yunli = yunli.Yunli(username,password)
                self.yunli.login()
                if self.yunli.testIfLogin() == True:
                    print('New Yunli success')
                    self.username = self.yunli.username
                    self.password = self.yunli.psw_original
                else:
                    self.yunli.login()
                    if self.yunli.testIfLogin() == True:
                        print('New Yunli success')
                        self.username = self.yunli.username
                        self.password = self.yunli.psw_original
            else:
                #如果没有传入了用户名密码
                self.yunli = yunli.Yunli()
                self.yunli.loginWithWindow()
                if self.yunli.testIfLogin() == False:
                    self.yunli.loginWithWindow()
                else:
                    print('New Yunli success')
                    self.username = self.yunli.username
                    self.password = self.yunli.psw_original


        if mFuxi != None:
            self.fuxi = mYunli
            try:
                #传入的fuxi对象  可以登录  说明传入的是Fuxi()  Fuxi().login()
                if fuxi.testIfLogin(self.fuxi.opener,self.fuxi.username) == False:
                    self.fuxi.loginWithWindow()
                else:
                    print('Parameter Fuxi success')

            except:
                #传入的fuxi对象  无法登陆  说明传入的是Fuxi()   没有 Fuxi().login()
                self.fuxi.loginWithWindow()
                if fuxi.testIfLogin(self.fuxi.opener,self.fuxi.username) == False:
                    self.fuxi.loginWithWindow()
                else:
                    print('Parameter Fuxi success')
        #外部没有传入Fuxi对象 自己创建
        else:
            #如果传入了用户名密码
            if username !=None and password !=None:
                self.fuxi = fuxi.Fuxi(username,password)
                self.fuxi.login()
                if fuxi.testIfLogin(self.fuxi.opener,self.fuxi.username) == True:
                    print('New Fuxi success')
                else:
                    self.yunli.login()
                    if fuxi.testIfLogin(self.fuxi.opener,self.fuxi.username) == True:
                        print('New Fuxi success')
            else:
                #如果没有传入了用户名密码
                self.fuxi = fuxi.Fuxi()
                self.fuxi.loginWithWindow()
                if fuxi.testIfLogin(self.fuxi.opener,self.fuxi.username) == False:
                    self.fuxi.loginWithWindow()
                else:
                    print('New Fuxi success')

        if self.center ==None:
            self.loginWithWindow()
        else:
            self.saveLoginInfo()
        #old init
        '''
        #载入之前的登录信息
        self.loadLoginInfo()
        if self.center !=None and self.username!=None and self.password!=None and self.yunli!=None:
            self.loginWithWindow()
            if self.yunli.testIfLogin() == False:
                self.yunli.loginWithWindow()
            else:
                print('Load login info success')  
                if self.yunli.getCenterCode(self.center) is not None:
                    print('Welcome '+self.center)
                    self.isInit =True
                    self.saveLoginInfo()
                    return
                else:
                    self.showInfoWindow('错误', '所监控的分拨不存在！')
                    self.loginWithWindow()
        
                
        #载入登录信息失败,以参数初始化self.center
        if self.center ==None:
            if  center != None:
                self.center = center
            else:
                self.loginWithWindow()
        
        if self.center =='':
            return
        
        if self.center !=None:
            #初始化yunli
            if self.yunli ==None:
                #外部传入yunli对象  
                if mYunli != None:
                    self.yunli = mYunli
                    try:
                        #传入的yunli对象  可以登录  说明传入的是Yunli()  Yunli().login()
                        if self.yunli.testIfLogin() == False:
                            self.yunli.loginWithWindow()
                        else:
                            print('Parameter Yunli success')  
                            self.username = self.yunli.username
                            self.password = self.yunli.psw_original
                    except:
                        #传入的yunli对象  无法登陆  说明传入的是Yunli()  没有 Yunli().login()
                        self.yunli.loginWithWindow()
                        if self.yunli.testIfLogin() == False:
                            self.yunli.loginWithWindow()
                        else:
                            print('Parameter Yunli success')  
                        self.username = self.yunli.username
                        self.password = self.yunli.psw_original  
                #外部没有传入Yunli对象 自己创建
                else:
                    #如果传入了用户名密码
                    if username !=None and password !=None:
                        self.yunli = yunli.Yunli(username,password)
                        self.yunli.login()
                        if self.yunli.testIfLogin() == True:
                            print('New Yunli success')  
                            self.username = self.yunli.username
                            self.password = self.yunli.psw_original  
                        else:
                            self.yunli.login()
                    else:
                        #如果没有传入了用户名密码
                        self.yunli = yunli.Yunli()
                        self.yunli.loginWithWindow()
                        if self.yunli.testIfLogin() == False:
                            self.yunli.loginWithWindow()
                        else:
                            print('New Yunli success')  
                            self.username = self.yunli.username
                            self.password = self.yunli.psw_original
                            self.username = self.yunli.username
                            self.password = self.yunli.psw_original    
            else:
                if self.yunli.testIfLogin() == False:
                    self.yunli.loginWithWindow()
                else:
                    print('Load Yunli success')  
                    self.username = self.yunli.username
                    self.password = self.yunli.psw_original
            
            #检查self.center的正确性
            if self.yunli !=None:
                if self.yunli.getCenterCode(self.center) is not None:
                    print('Login success')  
                    print('Welcome '+self.center)
                    self.isInit = True
                    self.saveLoginInfo()
                else:
                    self.loginWithWindow()
            
            if self.center !=None and self.username!=None and self.password!=None and self.yunli!=None:
                self.isInit = True
                self.saveLoginInfo()
            else:
                self.isInit =False
            '''


    def setMonitorCenter(self,center):
        self.center = center
    
    def showInfoWindow(self,title,msg):
        '''
        not finish dont use it
        '''
        def buttonCallBack():
            app.destroy()
        
        app = tk.Tk()
        app.resizable(width=False, height=False)
        app.title(title)
        app.wm_attributes('-topmost', 1)
        screenwidth, screenheight = app.maxsize()
        width = 200
        height = 100
        size = '%dx%d+%d+%d' % (width, height, (screenwidth - width)/2, (screenheight - height)/2)
        app.geometry(size)   
        
        label = tk.Label(app,text=msg,font=('微软雅黑',12))
        label.pack(pady=10)
        
        
        
        btn = tk.Button(app,text='确   定',command=buttonCallBack,font=('微软雅黑',10))
        btn.pack(pady=5)
        
        app.mainloop()
     
    def saveLoginInfo(self):     
        data = {'username':self.username,'password':self.password,'center':self.center,'yunli':self.yunli,'fuxi':self.fuxi}
        pickleToFile(data, 'leaveMonitor_login_data.pkl')
    
    def loadLoginInfo(self):
        data = loadPklFile('leaveMonitor_login_data.pkl')
        if data is not None:
            self.username = data['username']
            self.password = data['password']
            self.center = data['center']
            self.yunli = data['yunli']
            self.fuxi = data['fuxi']

            
    def loginWithWindow(self):
        '''
        '界面登录
        '''
        def buttonCallBack():
            #如果为第一次登录
            if self.center ==None:
                self.center = entry.get()
                #验证输入的center是否正确
                if self.yunli !=None:
                    if self.yunli.getCenterCode(self.center) is not None:
                        print('Welcome '+self.center)
                        self.saveLoginInfo()
                        app.quit()
                        app.destroy()
                        return
                    else:
                        messagebox.showerror('错误', '要监控的分拨不存在！')
                        app.quit()
                        app.destroy()
                        self.loginWithWindow()
                else:
                    messagebox.showerror('错误', '初始化未完成！重新初始化...')
                    app.quit()
                    app.destroy()
                    self.__init__(center=self.center, mYunli=self.yunli, username=self.username, password=self.password)
                    self.loginWithWindow()
            else:
                if self.center == entry.get():
                    #验证输入的center是否正确
                    if self.yunli !=None:
                        if self.yunli.getCenterCode(self.center) is not None:
                            print('Welcome '+self.center)
                            self.saveLoginInfo()
                            app.quit()
                            app.destroy()
                            return
                        else:
                            messagebox.showerror('错误', '要监控的分拨不存在！')
                            app.quit()
                            app.destroy()
                            self.__init__(center=self.center)
                            self.loginWithWindow()
                    else:
                        messagebox.showerror('错误', '初始化未完成！重新初始化...')
                        app.quit()
                        app.destroy()
                        self.__init__(center=self.center, mYunli=self.yunli, username=self.username, password=self.password)
                        self.loginWithWindow()
                else:
                    self.center = entry.get()
                    #验证输入的center是否正确
                    if self.yunli !=None:
                        if self.yunli.getCenterCode(self.center) is not None:
                            print('Welcome '+self.center)
                            self.saveLoginInfo()
                            app.quit()
                            app.destroy()
                            return
                        else:
                            messagebox.showerror('错误', '要监控的分拨不存在！')
                            app.quit()
                            app.destroy()
                            self.loginWithWindow()
                    else:
                        messagebox.showerror('错误', '初始化未完成！重新初始化...')
                        app.quit()
                        app.destroy()
                        self.__init__(center=self.center, mYunli=self.yunli, username=self.username, password=self.password)
                        self.loginWithWindow()
        
        
        app = tk.Tk()
        app.resizable(width=False, height=False)
        app.title("发车监控登录")
        app.wm_attributes('-topmost', 1)
        screenwidth, screenheight = app.maxsize()
        width = 250
        height = 120
        size = '%dx%d+%d+%d' % (width, height, (screenwidth - width)/2, (screenheight - height)/2)
        app.geometry(size)   
        
        frame = tk.Frame(app) 
        label = tk.Label(frame,text="要监控的分拨：",font=('微软雅黑',11))
        label.pack(side=tk.LEFT)
        entry = tk.Entry(frame,width=14)
        entry.pack(side=tk.RIGHT)
        frame.pack(pady=20)
        
        self.loadLoginInfo()
        if self.center !=None:
            entry.insert(0, self.center)
        else:
            entry.insert(0,'')
        
        
        btn = tk.Button(app,text='确   定',command=buttonCallBack,font=('微软雅黑',11))
        btn.pack(pady=5)
        
        app.mainloop()
        
    def getSendLoadWeightListByJobCode(self,jobCode):
        '''
        using api
        get load weight rate by jobcode
        "KYZC6576-190110" ==> [('南京', 7076.41), ('淮安', 8295.09)]  load weight list
        "出发装载率   如果是只装不卸  得到装载货量之和"
        
        return [('南京',3052.36),('苏州',7052.36)...]
        '''
        jobDetail = self.yunli.findDetailByJobCode(jobCode)
        if jobDetail is not None:
            jobCode = yunli.getValueInDic(jobDetail,'code') #"BEST-1373-180722"
            laneName = yunli.getValueInDic(jobDetail,'planRouteName') #'南京-泰州'
            adjustRouteName = yunli.getValueInDic(jobDetail,'adjustRouteName') #更改线路
            #获取真实线路
            realRouteName = ''
            if adjustRouteName != ' ':
                realRouteName = adjustRouteName
            else:
                realRouteName = laneName
           
            scanCode = yunli.getValueInDic(jobDetail,'scanCode')
            returnList = []
            for n in range(len(realRouteName.split("-"))-1):
                costCenter = self.yunli.getCenterCode(realRouteName.split("-")[n])
                realLoadsWeightList = self.fuxi.getJobCodeSendLoadWeightDetail(centerCode=costCenter,scanCode=scanCode)
                sendloads = 0
                if  realLoadsWeightList is not None:
                    for i in realLoadsWeightList:
                        sendloads += i['weight']
                    returnList.append((realRouteName.split("-")[n],sendloads))
                else:
                    returnList.append((realRouteName.split("-")[n],0))
            return returnList
        else:
            print('LeaveMonitor getSendLoadWeightListByJobCode fail')
            return None
        
        
    def startMonitorWithActualLeaveList(self,delaySecond=None,updatePeriodMinute=None):
        '''
        using api
        '已经发车的实时监控
        '''
        if delaySecond is None:
            delaySecond = 20
            
        if updatePeriodMinute is None:
            updatePeriodMinute = 5
            
        #初始化开始时间
        if self.firstStartMonitorTimeLong is None:
            self.firstStartMonitorTimeLong = int(yunli.getCurrentLongTime())
        #初始化列表
        if self.firstStartLeaveList is None:
            nowLeaveReap = self.yunli.getActualLeaveList(thisCenter=self.center,actualTimeBegin=self.firstStartMonitorTimeLong-5*60*1000,actualTimeEnd=None)    
            nowLeaveList = extractListFromActualLeaveList(nowLeaveReap)
            if nowLeaveList is not None:
                self.firstStartLeaveList = nowLeaveList
            else:
                raise Exception('startMonitorWithActualLeaveList nowLeaveList is None')
            #print(self.firstStartLeaveList)
            #print(len(self.firstStartLeaveList))
        #开始监控
        print('start monitor actual leave list...')
        #第一次启动先获取一遍，再开始循环
        nowLeaveList = extractListFromActualLeaveList(self.yunli.getActualLeaveList(thisCenter=self.center,actualTimeBegin=None,actualTimeEnd=None))
        if nowLeaveList is not None and self.firstStartLeaveList is not None:
            for each in nowLeaveList:
                if isItemInLeaveList(each, self.firstStartLeaveList) == False:
                    self.firstStartLeaveList.append(each)
                    task = threading.Thread(target=self.popWindow,args=(each,))
                    task.start()
                    time.sleep(1)
        else:
            print("start monitor with ActualArrivalList fail")
            print("reStart")
            try:
                self.startMonitorWithActualLeaveList(delaySecond, updatePeriodMinute)
            except:
                raise Exception('startMonitorWithActualLeaveList nowLeaveList is None')
        #第一次启动后，下面开始主循环
        self.isMonitorWithActualLeaveList = True
        while self.isMonitorWithActualLeaveList ==True:
            #print(self.firstStartLeaveList)
            nowLeaveList = None
            nowTimeLong = int(yunli.getCurrentLongTime())
            nowTimeStr = yunli.parseLongTimeToDateString(nowTimeLong)
            nowMinute = int(nowTimeStr.split(":")[1])
            if nowMinute % updatePeriodMinute == 0:
                #print('geting...')
                nowLeaveList = extractListFromActualLeaveList(self.yunli.getActualLeaveList(thisCenter=self.center,actualTimeBegin=None,actualTimeEnd=None))
                #print(len(nowLeaveList))
                if nowLeaveList is not None and self.firstStartLeaveList is not None:
                    for each in nowLeaveList:
                        if isItemInLeaveList(each, self.firstStartLeaveList) == False:
                            #print(each['laneName'])
                            self.firstStartLeaveList.append(each)
                            task = threading.Thread(target=self.popWindow,args=(each,))
                            task.start()
                            time.sleep(1)
                else:
                    print("start monitor with ActualArrivalList fail")
                    print("reStart")
                    try:
                        self.startMonitorWithActualLeaveList(delaySecond, updatePeriodMinute)
                    except:
                        raise Exception('startMonitorWithActualLeaveList nowLeaveList is None')
                time.sleep(delaySecond)
            else:
                time.sleep(delaySecond)
            
            
    def startMonitorWithPlanLeaveList(self,delaySecond=None):
        '''
        using api
        '计划发车的实时监控
        '''
        
        #print(yunli.parseLongTimeToDateString(1546961010554))
        #print(yunli.parseLongTimeToDateString(1546988940169))
        if delaySecond==None:
            delaySecond = 5
        
        
        #初始化列表
        if self.firstStartLeaveList is None:
            self.firstStartLeaveList = []
            
        self.isMonitorWithPlanLeaveList = True
        print("start monitor with PlanLeaveList... ")
        while self.isMonitorWithPlanLeaveList == True:
            #print('plan list geting...')
            #取得未发车计划列表
            planList=extractListFromPlanLeaveList(self.yunli.getPlanLeaveList(thisCenter=self.center,planTimeBegin=None,planTimeEnd=None))  
            #print(len(planList))
            if planList is not None:
                for each in planList:
                    #print(each['laneName'])
                    task = threading.Thread(target=self.popWindowIfLeave,args=(each,))
                    task.start()
                    
                
            
            time.sleep(delaySecond)
        
    
    def startMonitorWithEarlyWarning(self,earlyMinutes=None,delaySecond=None):
        '''
        using api
        '发车前earlyMinutes分钟内实时监控
        
        '''
        #默认提前20分钟预警
        if earlyMinutes ==None:
            earlyMinutes = 30
        
        if delaySecond == None:
            delaySecond = 5
        
        #初始化列表
        if self.firstStartLeaveList is None:
            self.firstStartLeaveList = []
        #print(yunli.parseLongTimeToDateString(1547265000000))
        #print(yunli.parseLongTimeToDateString(1547383800000))
        
        print('start monitor with early warning...')
        self.isMonitorWithEarlyWarning = True
        while self.isMonitorWithEarlyWarning == True:
            try:
                opDate = yunli.getOperationStartAndEndDateNormalFormat()
                planTimeBegin = opDate[0] + ' 18:00:00'
                planTimeEnd = opDate[1] + ' 18:00:00'
                #print('geting....')
                planList=extractListFromPlanLeaveList(self.yunli.getPlanLeaveList(thisCenter=self.center,planTimeBegin=planTimeBegin,planTimeEnd=planTimeEnd))  
                #print(planList)
                #print(len(planList))
                if planList is not None:
                    for each in planList:
                        #print(each['laneName'])
                        #本站计划出发时间
                        planTime = int(each['planTime'])
                        #现在的时间
                        nowTime = int(yunli.getCurrentLongTime())
                        if planTime - nowTime <= earlyMinutes*60*1000:
                            task = threading.Thread(target=self.popEarlyWarningWindow,args=(each,earlyMinutes))
                            task.start()
                            time.sleep(1)
                    
                
                time.sleep(delaySecond)
            except:
                break
        
    def startEarlyWarningMonitor(self):
        startMonitorWithEarlyWarningTask = threading.Thread(target=self.startMonitorWithEarlyWarning)
        startMonitorWithEarlyWarningTask.start()
    
    def stopEarlyWarningMonitor(self):
        print('stop Monitor With Early Warning...')
        self.isMonitorWithEarlyWarning =False
    
    def startMonitor(self):
        '''
        using api
        '开始实时出发监控'
        '''
        print('start Monitor...')
        startMonitorWithActualLeaveListTask = threading.Thread(target=self.startMonitorWithActualLeaveList)
        startMonitorWithPlanLeaveListTask = threading.Thread(target=self.startMonitorWithPlanLeaveList)
        
        startMonitorWithActualLeaveListTask.start()
        startMonitorWithPlanLeaveListTask.start()
    
    def stopMonitor(self):
        print('stop monitor...')
        self.isMonitorWithActualLeaveList =False
        self.isMonitorWithPlanLeaveList = False
    
        
        
    def popWindow(self,eachItem,actualTime=None):
        '''
        using api
        
        using build api popLeaveInfoWindow() to pop a window
        '''
        #初始化参数
        laneName = yunli.getValueInDic(eachItem,'laneName')
        if actualTime !=None:
            actualTime = actualTime
        else:
            actualTime = yunli.getValueInDic(eachItem,'actualTime')
        jobCode = yunli.getValueInDic(eachItem,'jobCode')
        pinCode = eachItem['pinCode']
        licensePlate = yunli.getValueInDic(eachItem,'licensePlate')
        trailerLicensePlate = yunli.getValueInDic(eachItem,'trailerLicensePlate')
        
        self.popLeaveInfoWindow(laneName, actualTime, jobCode, pinCode, licensePlate, trailerLicensePlate)
        
    def popWindowIfLeave(self,eachItem): 
        '''
        '计划发车监控，如果未发车，但是检查到了出港考勤，则弹窗
        '''
        
        jobCode = eachItem['jobCode']
        recordList = self.yunli.getClientBarCodeRecordListByJobCode(jobCode)
        leaveInfo = getLeaveInfoByRecordList(recordList,self.center)
        if leaveInfo[0]:
            eachItem['scanTime'] = leaveInfo[1]['scanTime']
        if leaveInfo[0] == True and isItemInLeaveList(eachItem, self.firstStartLeaveList) == False:
            #print(recordList)
            self.firstStartLeaveList.append(eachItem)
            self.popWindow(eachItem,leaveInfo[1]['scanTime'])
            
    def popEarlyWarningWindow(self,eachItem,earlyMinutes):
        '''
        '发车前预警窗口
        
        eachItem  传入的计划发车列表中，还未出港的eachItem
        earlyMinutes  提前多少分钟
        '''
        #如果该item已经显示，则不再显示
        if isItemInLeaveList(eachItem, self.alreadlyPopEarlyWarningList) ==True:
            #print(eachItem['laneName'],'已经显示')
            return
        #如果该item还未被显示
        else:
            #获取考勤记录
            jobCode = eachItem['jobCode']
            recordList = self.yunli.getClientBarCodeRecordListByJobCode(jobCode)
            leaveInfo = getLeaveInfoByRecordList(recordList,self.center)
            #始发分拨未发车，本站是经停分拨，则不显示
            laneName = eachItem['laneName']
            if self.center.replace('分拨','') != laneName.split('-')[0]:
                if ifArrivalInCenterByRecordList(recordList, self.center)[0] ==False:
                    #print(laneName,'上一站还未发车！！')
                    return
            #已考勤，则显示已出发窗口
            if leaveInfo[0]==True:
                eachItem['scanTime'] = leaveInfo[1]['scanTime']
                if leaveInfo[0] == True and isItemInLeaveList(eachItem, self.firstStartLeaveList) == False:
                    #print(recordList)
                    self.firstStartLeaveList.append(eachItem)
                    self.alreadlyPopEarlyWarningList.append(eachItem)
                    self.popWindow(eachItem,leaveInfo[1]['scanTime'])
            #未考勤，则显示提前预警窗口
            else:
                #本站计划出发时间
                planTime = int(eachItem['planTime'])
                #现在的时间
                nowTime = int(yunli.getCurrentLongTime())
                if planTime - nowTime <= earlyMinutes*60*1000:
                    minutes = int((planTime - nowTime)/(60*1000))
                    seconds = int(((planTime - nowTime)%(60*1000))/1000)
                    #print(str(minutes) + ':'+str(seconds))
                    #print(eachItem['laneName'],yunli.parseLongTimeToDateString(planTime),yunli.parseLongTimeToDateString(nowTime))
                    self.alreadlyPopEarlyWarningList.append(eachItem)
                    '''
                    def _async_raise(tid, exctype):
                        """raises the exception, performs cleanup if needed"""
                        tid = ctypes.c_long(tid)
                        if not inspect.isclass(exctype):
                            exctype = type(exctype)
                        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
                        if res == 0:
                            raise ValueError("invalid thread id")
                        elif res != 1:
                            # """if it returns a number greater than one, you're in trouble,
                            # and you should call it again with exc=NULL to revert the effect"""
                            ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
    
                    
                    def stop_thread(thread):
                        _async_raise(thread.ident, SystemExit)
                    '''
                    '''
                    global isDoTimeRemain
                    global isDoSendLoadWeight
                    global isDoFindSeal
                    global isDoCheckIfLeave
                    
                    isDoTimeRemain =True
                    isDoSendLoadWeight =True
                    isDoFindSeal = True
                    isDoCheckIfLeave = True
                    '''
                    def doTimeRemain():
                        '''
                        '显示倒计时'
                        '''
                        #global isDoTimeRemain
                        #nonlocal isDoTimeRemain
                        time.sleep(1)
                        while True:
                            #print(laneName,'doTimeRemain')
                            nowTime = int(yunli.getCurrentLongTime())
                            minutes = int((planTime - nowTime)/(60*1000))
                            seconds = int(((planTime - nowTime)%(60*1000))/1000)
                            showStr = '剩余：'+str(minutes) + ':'+str(seconds)
                            try:
                                if text1 is not None:
                                    text1.config(state=tk.NORMAL)
                                    text1.delete(1.0,tk.END)
                                    text1.insert(tk.INSERT, showStr)
                                    text1.tag_add('tag1', '1.0', '1.end') 
                                    text1.tag_config('tag1', justify='center') 
                                    text1.tag_config('tag1', spacing1=6)
                                    text1.config(state=tk.DISABLED)
                            except:
                                break
                            time.sleep(1)
                            
                    def doSendLoadWeight():
                        '''
                        '获取装载数据'
                        '''
                        #global isDoSendLoadWeight
                        #nonlocal isDoSendLoadWeight
                        time.sleep(1)
                        while True:
                            #print(laneName,'doSendLoadWeight')
                            try:
                                text2.config(state=tk.NORMAL)
                                text2.delete(1.0,tk.END)
                                text2.insert(tk.INSERT, 'geting...')
                                #装载数据
                                jobCode = eachItem['jobCode']
                                licensePlate = yunli.getValueInDic(eachItem,'licensePlate')
                                #获取装载货量信息
                                weightInfo = self.getSendLoadWeightListByJobCode(jobCode)
                                #获取车辆的运力
                                containerWeight = self.yunli.getPlateContainerWeight(licensePlate)
                                allWeight = sumAllLoadWeightFromWeightInfoList(weightInfo)
                                weightInfoStr=''
                                for each in weightInfo:
                                    weightInfoStr = weightInfoStr+ each[0] + ':' + '%.2f'%(each[1]) + '\n'
                                #停开情况
                                oldjobCodeInfo = self.yunli.ifJobCodeTerminatedYesterday(jobCode)
                                oldWeight = 0
                                if oldjobCodeInfo[0] ==True:
                                    oldjobCode = yunli.jobcodeDateAddOrMinus(jobCode, -1)
                                    oldWeight = sumAllLoadWeightFromWeightInfoList(self.getSendLoadWeightListByJobCode(oldjobCode))
                                    weightInfoStr += '昨日装载：%.2f'%(oldWeight) + '\n'
                                
                                weightInfoStr += '一共装载：' + '%.2f'%(allWeight+oldWeight) + '\n'
                                weightInfoStr += '装载率：' + '%.2f'%((allWeight+oldWeight)/containerWeight*100) + '%'
                                text2.delete(1.0,tk.END)
                                text2.insert(tk.INSERT, weightInfoStr)
                                text2.config(state=tk.DISABLED)
                            except:
                                break
                            time.sleep(30)
                            
                    def doFindSeal():
                        '''
                        '获取封签'
                        '''
                        #global isDoFindSeal
                        #nonlocal isDoFindSeal
                        time.sleep(1)
                        while True:
                            #print(laneName,'doFindSeal')
                            try:
                                text3.config(state=tk.NORMAL)
                                text2.delete(1.0,tk.END)
                                text3.insert(tk.INSERT, 'geting...')
                                #装载数据
                                jobCode = eachItem['jobCode']
                                seal = self.yunli.findCenterLeaveTaskSeal(jobCode, self.center)
                                if seal ==None:
                                    seal = ' '
                                text3.delete(1.0,tk.END)
                                text3.insert(tk.INSERT, seal)
                                text3.config(state=tk.DISABLED)
                            except:
                                break
                            time.sleep(30)
                        
                    def doCheckIfLeave():
                        '''
                        '检查是否已经出港'
                        '''
                        #global isDoCheckIfLeave
                        #nonlocal isDoCheckIfLeave
                        time.sleep(1)
                        while True:
                            #print(laneName,'doCheckIfLeave')
                            try:
                                #获取考勤记录
                                jobCode = eachItem['jobCode']
                                recordList = self.yunli.getClientBarCodeRecordListByJobCode(jobCode)
                                leaveInfo = getLeaveInfoByRecordList(recordList,self.center)
                               
                                #已考勤，则显示已出发窗口
                                if leaveInfo[0]==True:
                                    eachItem['scanTime'] = leaveInfo[1]['scanTime']
                                    if leaveInfo[0] == True and isItemInLeaveList(eachItem, self.firstStartLeaveList) == False:
                                        #print(recordList)
                                        self.firstStartLeaveList.append(eachItem)
                                        self.alreadlyPopEarlyWarningList.append(eachItem)
                                        self.popWindow(eachItem,leaveInfo[1]['scanTime'])
                                        try:
                                            app.destroy()
                                        except:
                                            break
                                    else:
                                        break
                            except:
                                break
                            time.sleep(5)
                            
                            
                        
                    def stopMainloop():
                        '''
                        nonlocal isDoTimeRemain
                        nonlocal isDoSendLoadWeight
                        nonlocal isDoFindSeal
                        nonlocal isDoCheckIfLeave
                        isDoTimeRemain = False
                        isDoSendLoadWeight = False
                        isDoFindSeal =False
                        isDoCheckIfLeave = False
                        doTimeRemainTask=None
                        '''
                        '''
                        stop_thread(doTimeRemainTask)
                        stop_thread(doSendLoadWeightTask)
                        stop_thread(doFindSealTask)
                        stop_thread(doCheckIfLeaveTask)
                        '''
                        #print(laneName,'guanbi....')
                        app.destroy()
                        
                    def buttonCallBack():
                        stopMainloop()
                        
                    def on_closing():
                        pass
                    
                    def updateLoop():
                        #倒计时
                        doTimeRemainTask = threading.Thread(target=doTimeRemain)
                        doTimeRemainTask.start()
                        #装载货量
                        doSendLoadWeightTask =threading.Thread(target=doSendLoadWeight)
                        doSendLoadWeightTask.start()
                        #封签
                        doFindSealTask = threading.Thread(target=doFindSeal)
                        doFindSealTask.start()
                        #检查发车情况
                        doCheckIfLeaveTask = threading.Thread(target=doCheckIfLeave)
                        doCheckIfLeaveTask.start()
                    
                    app = tk.Tk()
                    app.wm_attributes('-topmost', 1)
                    screenwidth, screenheight = app.maxsize()
                    width = 300
                    height = 500
                    size = '%dx%d+%d+%d' % (width, height, (screenwidth - width)/2, (screenheight - height)/2)
                    app.geometry(size)
                    app.resizable(width=False, height=False)
                    app.title("发车提前预警")
                    
                    #print(eachItem['laneName'],'开始创建')
                    #strVar = tk.StringVar()
                    #print(strVar)
                    
                    #预警车线
                    label1 = tk.Label(app,text=eachItem['laneName'] +'预警！',font=('黑体',16),pady=20)
                    label1.pack()
                    #计划出发时间
                    label2 = tk.Label(app,text='发车时间：'+yunli.parseLongTimeToDateString(planTime)[:-3],font=('微软雅黑',12),pady=10)
                    label2.pack()
                    #显示剩余时间文本框
                    text1 = tk.Text(app,height=2,font=('黑体',12))
                    text1.pack()
                    #doTimeRemainTask = threading.Thread(target=doTimeRemain)
                    #doTimeRemainTask.start()
                    #线路信息
                    laneName = yunli.getValueInDic(eachItem,'laneName')
                    jobCode = yunli.getValueInDic(eachItem,'jobCode')
                    pinCode = eachItem['pinCode']
                    licensePlate = yunli.getValueInDic(eachItem,'licensePlate')
                    trailerLicensePlate = yunli.getValueInDic(eachItem,'trailerLicensePlate')
                    phoneInfo = self.yunli.getPhoneNumberBylicensePlate(licensePlate)
                    textStr = '车线:'+laneName+'\n'\
                            +'任务单：'+jobCode+'\n'\
                            +'考勤码：'+pinCode+'\n'\
                            +'车牌：'+licensePlate+'  ' + trailerLicensePlate+'\n'\
                            +'电话：'+str(phoneInfo[0])+ '  ' + phoneInfo[1]
                    infotext = tk.Text(app,font=('宋体',10),height=6)
                    infotext.insert(tk.INSERT, textStr)
                    infotext.config(state=tk.DISABLED)
                    infotext.pack(pady=15)
                    #装载数据
                    frame1 = tk.Frame(app)
                    label3 = tk.Label(frame1,text="装载货量：")
                    label3.pack(side=tk.LEFT)
                    text2 = tk.Text(frame1,font=('宋体',10),height=6,width = 25)
                    text2.pack()
                    frame1.pack(pady=15)
                    #doSendLoadWeightTask =threading.Thread(target=doSendLoadWeight)
                    #doSendLoadWeightTask.start()
                    #封签数据
                    frame2 = tk.Frame(app)
                    label4 = tk.Label(frame2,text="封签号码：")
                    label4.pack(side=tk.LEFT)
                    text3 = tk.Text(frame2,font=('宋体',10),height=1,width = 25)
                    text3.pack(side=tk.RIGHT)
                    frame2.pack(pady=15)
                    #doFindSealTask = threading.Thread(target=doFindSeal)
                    #doFindSealTask.start()
                    
                    #检查是否发车
                    #doCheckIfLeaveTask = threading.Thread(target=doCheckIfLeave)
                    #doCheckIfLeaveTask.start()
                    
                    btn1 = tk.Button(app,text='确 定',font=('黑体',12),command=buttonCallBack)
                    btn1.pack(pady=15)
                   
                    app.protocol("WM_DELETE_WINDOW", on_closing)
                    updateLoop()
                    app.mainloop()
                                
                    
                pass
    
    
    def popLeaveInfoWindow(self,laneName=None,actualTime=None,jobCode=None,pinCode=None,licensePlate=None,trailerLicensePlate=None):
        '''
        build in api
        '弹出一个出发提示窗口
        laneName  线路
        actualTime  扫描时间
        jobCode   任务单
        pinCode   C码
        licensePlate  车牌
        trailerLicensePlate   车挂
        '''
        
        #初始化参数
        if laneName == None:
            laneName = ''
        if actualTime == None:
            actualTime = ''
        if jobCode == None:
            jobCode = ''
        if pinCode == None:
            pinCode = ''
        if licensePlate == None:
            licensePlate = ''
        if trailerLicensePlate == None:
            trailerLicensePlate = ''
            
        def buttonCallBack():
            
            if logEntry is not None:
                logStr = logEntry.get()
                if logStr.strip() !='':
                    if self.yunli.addLogByJobCode(jobCode,logStr)[0]:
                        app.destroy()
                    else:
                        pass
                else:
                    app.destroy()
            
            
        def entryReturnCallBack(event):
            buttonCallBack()
            
        app = tk.Tk()
        app.wm_attributes('-topmost', 1)
        screenwidth, screenheight = app.maxsize()
        width = 300
        height = 350
        size = '%dx%d+%d+%d' % (width, height, (screenwidth - width)/2, (screenheight - height)/2)
        app.geometry(size)
        app.resizable(width=False, height=False)
        app.title("发车预警")
        
        
        
        label = tk.Label(app,text=laneName +'出发了',font=('黑体',16),pady=20)
        label.pack()
        
        if actualTime != '':
            actualTimeStr = yunli.parseLongTimeToDateString(int(actualTime))
        else:
            actualTimeStr = ''
        textStr = '车线:'+laneName+'\n'\
                    +'任务单：'+jobCode+'\n'\
                    +'考勤码：'+pinCode+'\n'\
                    +'车牌：'+licensePlate+'  ' + trailerLicensePlate+'\n'\
                    +'打卡时间：'+actualTimeStr
        text = tk.Text(app,font=('宋体',10),height=6)
        
        text.insert(tk.INSERT, textStr)
        text.config(state=tk.DISABLED)
        text.pack()
        
        frame = tk.Frame(app)
        label2 = tk.Label(frame,text="装载货量：")
        label2.pack(side=tk.LEFT)
        text2 = tk.Text(frame,font=('宋体',10),height=6,width = 25)
        
        #获取装载货量信息
        weightInfo = self.getSendLoadWeightListByJobCode(jobCode)
        #获取车辆的运力
        containerWeight = self.yunli.getPlateContainerWeight(licensePlate)
        
        allWeight = sumAllLoadWeightFromWeightInfoList(weightInfo)
        
        weightInfoStr=''
        for each in weightInfo:
            weightInfoStr = weightInfoStr+ each[0] + ':' + '%.2f'%(each[1]) + '\n'
        #停开情况
        oldjobCodeInfo = self.yunli.ifJobCodeTerminatedYesterday(jobCode)
        oldWeight = 0
        if oldjobCodeInfo[0] ==True:
            oldjobCode = yunli.jobcodeDateAddOrMinus(jobCode, -1)
            oldWeight = sumAllLoadWeightFromWeightInfoList(self.getSendLoadWeightListByJobCode(oldjobCode))
            weightInfoStr += '昨日装载：%.2f'%(oldWeight) + '\n'
        
        weightInfoStr += '一共装载：' + '%.2f'%(allWeight+oldWeight) + '\n'
        weightInfoStr += '装载率：' + '%.2f'%((allWeight+oldWeight)/containerWeight*100) + '%'
        text2.insert(tk.INSERT, weightInfoStr)
        text2.config(state=tk.DISABLED)
        text2.pack()
        frame.pack(pady=20)
        
        frame2 = tk.Frame(app)
        label3 = tk.Label(frame2,text='备注：',font=('微软雅黑',10))
        label3.pack(side=tk.LEFT)
        logEntry = tk.Entry(frame2,width=27)
        logEntry.pack(side=tk.RIGHT)
        logEntry.bind('<Return>', entryReturnCallBack)
        frame2.pack()
        
        button = tk.Button(app,text='确定',font=('黑体',14),command=buttonCallBack)
        button.pack(pady = 10)
       
        app.mainloop()




        
        
if __name__ == "__main__":
    #yl = yunli.Yunli()
    #yl.loginWithWindow()
    #fx = fuxi.Fuxi()
    #fx.loginWithWindow()
    #monitor = LeaveMonitor(center='苏州',username='BG269073',password='Ll789456123')
    #monitor = LeaveMonitor(center='苏州',mYunli=yl,mFuxi=fx)
    #monitor = LeaveMonitor(center='苏州')
    monitor = LeaveMonitor()
    #monitor.popLeaveInfoWindow(jobCode='KYZC5833-190110',licensePlate='沪DL6568')
    #monitor.popLeaveInfoWindow(laneName='南京-淮安-北京',scanTime=None,jobCode='KYZC6115-190110',pinCode=None,licensePlate='京AHT322',trailerLicensePlate=None)
    #monitor.startMonitorWithActualLeaveList()
    #monitor.startMonitorWithPlanLeaveList()
    #monitor.popLeaveInfoWindow(jobCode='KYZC5833-190110',licensePlate='沪DL6568')
    #monitor.startMonitorWithEarlyWarning()
    t = threading.Thread(target=monitor.startMonitorWithEarlyWarning)
    t.start()
    #time.sleep(10)
    #monitor.stopEarlyWarningMonitor()
    
    
   
    