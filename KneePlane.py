import logging
import os
from typing import Annotated, Optional
import sys
import numpy as np
import math
import slicer.util
import vtk
import qt
from ast import literal_eval
from scipy.optimize import minimize
from math import atan2, asin, sqrt,cos, sin, radians
import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

#
# KneePlane
#


class KneePlane(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("KneePlane")  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["John Doe (AnyWare Corp.)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages



#
# KneePlaneWidget
#


class KneePlaneWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent=None) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation
        self.logic = None
        self._parameterNode = None
        self._parameterNodeGuiTag = None

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)


        uiWidget = slicer.util.loadUI(self.resourcePath("UI/KneePlane.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)
        uiWidget.setMRMLScene(slicer.mrmlScene)


        self.planePoits=np.array([[[ 26.02337837,  -9.75870705,  17.9810009 ],
                [  4.09119368,  15.38273907,  52.60262299],
                [ 27.1153183 , -25.06363297,  33.4731369 ],
                [ 24.84617805,   6.57620001,  24.46980286],
                [ 27.42753792, -21.2009716 ,  21.05237007]],
            [[ 27.43185806,  -9.48676395,  17.97990036],
                [  2.74365425,  16.84506226,  54.29030228],
                [ 28.19996643, -26.78960228,  34.69130325],
                [ 26.02665329,   6.64299297,  24.03082085],
                [ 29.09984589, -23.38258934,  22.70436096]],
            [[ 29.20111847,  -9.13559914,  17.97800064],
                [  3.35643864,  18.51843262,  55.00411987],
                [ 22.51490211, -27.72629547,  42.68426895],
                [ 27.12848663,   7.07448769,  23.76689148],
                [ 30.01587677, -23.92788315,  22.52571678]],
            [[ 29.20111847,  -9.13559914,  17.97800064],
                [  5.28588533,  20.57026291,  57.9031105 ],
                [ 21.47888374, -28.70822334,  46.11002731],
                [ 29.24750519,   8.71127605,  24.48480034],
                [ 30.89999962, -24.23026848,  22.03702545]],
            [[ 29.20111847,  -9.13559914,  17.97800064],
                [  5.85270691,  23.05169678,  60.28654099],
                [ 21.09650612, -30.24600601,  47.68890762],
                [ 30.85585403,  10.05577946,  24.61523628],
                [ 34.46922302, -26.14871788,  22.59331131]],
                [[ 29.20111847,  -9.13559914,  17.97800064],
                [  7.20682764,  23.6224575 ,  61.33934402],
                [ 23.2329483 , -32.42521667,  49.56483841],
                [ 31.82821846,  10.43430519,  25.68725395],
                [ 36.05748367, -26.62179184,  23.76049614]]])
        self.planeNormal=np.array([[ 0.00000000e+00, -0.00000000e+00, 1.00000000e+00],
                    [-1.22643894e-06, -9.94364794e-01,  1.06012534e-01],
                    [ 5.17413353e-07,  9.99843475e-01,  1.76924985e-02],
                    [ -6.10205166e-07,  -7.02040987e-01, 7.12136541e-01],
                    [7.07153645e-08, 7.02036904e-01, 7.12140566e-01]])

        self.FemurCropModel = None
        self.TibiaCropModel = None
        self.myssm=ssmFemur()
        self.setUpAll3DView()
        self.setUpCurve()
        self.onGenerateFemur()
        self.onGenerateTibia()
        self.onSetUpCameraPostion()



   



    def cleanup(self) -> None:
        """Called when the application closes and the module widget is destroyed."""
        self.removeObservers()

    def setUpCurve(self):
        # 添加painterCurve
        paint_Curve_widget = slicer.modules.paintcurve.widgetRepresentation()
        # 查找目标控件
        # 查找 qMRMLWidget 控件
        self.qMRML_widget = paint_Curve_widget.findChild(slicer.qMRMLWidget)
        if self.qMRML_widget is None:
            raise RuntimeError("qMRMLWidget not found in PaintCurve widget.")
        self.ui.painter_Curve_widget.layout().addWidget(self.qMRML_widget)

    
    def setUpAll3DView(self):
        """
        设置所有 3D 视图。

        该方法创建并配置多个 3D 视图节点，并将它们与 UI 中的 3D 视图小部件相关联。

        参数:
        无

        返回:
        无
        """
        self.viewList = []
        widget_bottom = CustomWindow()
        self.ui.widget_4.layout().addWidget(widget_bottom)
        # 为widget_bottom设置布局
        widget_bottom.setLayout(qt.QHBoxLayout())
        # 设置布局间距均为0
        widget_bottom.layout().setSpacing(0)
        # 设置上下左右边距均为0
        widget_bottom.layout().setContentsMargins(0, 0, 0, 0)
        for i in range(6):
            # 创建 MRML 视图节点
            viewOwnerNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScriptedModuleNode")
            viewLogic = slicer.vtkMRMLViewLogic()
            viewLogic.SetMRMLScene(slicer.mrmlScene)
            viewNode = viewLogic.AddViewNode(f"Test3DView_{i}")  # 为每个视图节点提供唯一名称
            viewNode.SetLayoutLabel(f"Test{i}")  # 为每个视图节点设置标签
            viewNode.SetLayoutColor(0, 0, 0)
            viewNode.SetBackgroundColor(0, 0, 0)
            viewNode.SetAndObserveParentLayoutNodeID(viewOwnerNode.GetID())
            # 创建 3D 视图小部件
            threeDViewWidget = slicer.qMRMLThreeDWidget()
            
            threeDViewWidget.setMRMLScene(slicer.mrmlScene)
            threeDViewWidget.setMRMLViewNode(viewNode)
            threeDViewWidget.show()
            if i<3:
                self.ui.widget_Top.layout().addWidget(threeDViewWidget)
            else:
                widget_bottom.layout().addWidget(threeDViewWidget)
            self.viewList.append(threeDViewWidget)
        self.viewButtonList=[]
        View1TopButton = ViewPopWidget1(1)
        View1TopButton.setParent(self.viewList[0])
        View1TopButton.setPositionByWidget(self.viewList[0],'top')
        View1TopButton.show()
        View1TopButton.LeftButton.connect('clicked()', self.onFemurRotateY1)
        View1TopButton.RightButton.connect('clicked()', self.onFemurRotateY2)
        self.viewButtonList.append(View1TopButton)

        View1BottomButton = ViewPopWidget1(2)
        View1BottomButton.setParent(self.viewList[0])
        View1BottomButton.setPositionByWidget(self.viewList[0],'bottom')
        View1BottomButton.show()
        self.viewButtonList.append(View1BottomButton)
        View1BottomButton.LeftButton.connect('clicked()', self.onFemurZMove2)
        View1BottomButton.RightButton.connect('clicked()', self.onFemurZMove1)


        View2TopButton = ViewPopWidget1(1)
        View2TopButton.setParent(self.viewList[1])
        View2TopButton.setPositionByWidget(self.viewList[1],'top')
        View2TopButton.show()
        View2TopButton.LeftButton.connect('clicked()', self.onFemurRotateZ2)
        View2TopButton.RightButton.connect('clicked()', self.onFemurRotateZ1)
        self.viewButtonList.append(View2TopButton)

        View2BottomButton = ViewPopWidget1(2)
        View2BottomButton.setParent(self.viewList[1])
        View2BottomButton.setPositionByWidget(self.viewList[1],'bottom')
        View2BottomButton.show()
        self.viewButtonList.append(View2BottomButton)
        View2BottomButton.LeftButton.connect('clicked()', self.onFemurYMove2)
        View2BottomButton.RightButton.connect('clicked()', self.onFemurYMove1)

        View3TopButton = ViewPopWidget1(1)
        View3TopButton.setParent(self.viewList[2])
        View3TopButton.setPositionByWidget(self.viewList[2],'top')
        View3TopButton.show()
        View3TopButton.LeftButton.connect('clicked()', self.onFemurRotateX2)
        View3TopButton.RightButton.connect('clicked()', self.onFemurRotateX1)
        self.viewButtonList.append(View3TopButton)
        
        
        View3BottomButton = ViewPopWidget1(1)
        View3BottomButton.setParent(self.viewList[2])
        View3BottomButton.setPositionByWidget(self.viewList[2],'bottom')
        View3BottomButton.show()
        self.viewButtonList.append(View3BottomButton)
        View3BottomButton.LeftButton.connect('clicked()', self.onFemurYMove1)
        View3BottomButton.RightButton.connect('clicked()', self.onFemurYMove2)
        View3BottomButton.setCenterNumber('毫米')

        View4TopButton = ViewPopWidget1(2)
        View4TopButton.setParent(self.viewList[3])
        View4TopButton.setPositionByWidget(self.viewList[3],'top')
        View4TopButton.show()

        View4TopButton.LeftButton.connect('clicked()', self.onTibiaZMove1)
        View4TopButton.RightButton.connect('clicked()', self.onTibiaZMove2)
        self.viewButtonList.append(View4TopButton)
        View4BottomButton = ViewPopWidget1(1)
        View4BottomButton.setParent(self.viewList[3])
        View4BottomButton.setPositionByWidget(self.viewList[3],'bottom')
        View4BottomButton.show()
        self.viewButtonList.append(View4BottomButton)
        View4BottomButton.LeftButton.connect('clicked()', self.onTibiaRotateY1)
        View4BottomButton.RightButton.connect('clicked()', self.onTibiaRotateY2)

        View5BottomButton = ViewPopWidget1(1)
        View5BottomButton.setParent(self.viewList[5])
        View5BottomButton.setPositionByWidget(self.viewList[5],'bottom')
        View5BottomButton.show()
        self.viewButtonList.append(View5BottomButton)
        View5BottomButton.LeftButton.connect('clicked()', self.onTibiaRotateX1)
        View5BottomButton.RightButton.connect('clicked()', self.onTibiaRotateX2)



        # 使得视图按钮随着视图大小的变化而变化
        self.view1Observer = slicer.util.getNode('vtkMRMLViewNodeTest3DView_0').AddObserver(vtk.vtkCommand.ModifiedEvent,self.updatePopWidgetPosition1)

    def updatePopWidgetPosition1(self):
        self.viewButtonList[0].setPositionByWidget(self.viewList[0],'top')
        self.viewButtonList[1].setPositionByWidget(self.viewList[0],'bottom')
        self.viewButtonList[2].setPositionByWidget(self.viewList[1],'top')
        self.viewButtonList[3].setPositionByWidget(self.viewList[1],'bottom')
        self.viewButtonList[4].setPositionByWidget(self.viewList[2],'top')
        self.viewButtonList[5].setPositionByWidget(self.viewList[2],'bottom')
        self.viewButtonList[6].setPositionByWidget(self.viewList[3],'top')
        self.viewButtonList[7].setPositionByWidget(self.viewList[3],'bottom')
        self.viewButtonList[8].setPositionByWidget(self.viewList[5],'bottom')
        

    def FemurNihe1(self,meshPoints, judge):
        ssm1 = ssm()
        ssm1.FilePath=self.resourcePath("static/asset/ssm")
        ssm1.Femur_list = meshPoints
        ssm1.judge = judge
        ssm1.preparPoints_femur()
        ssm1.FemurNihe(ssm1.Femur_list)
    
    def TibiaNihe(self,meshPoints, judge):
        ssm1 = ssm()
        ssm1.FilePath=self.resourcePath("static/asset/ssm")
        ssm1.Femur_list = meshPoints
        ssm1.judge = judge
        ssm1.preparPoints_tibia()
        ssm1.TibiaNihe(ssm1.Femur_list)


    def caculateFemur(self,path,outputPath,points,LorR):
        fromPoints=np.array(points)[0:8]
        #path="D:/scala/femur_full_out/15.vtk"
        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(path)
        reader.Update()
        polydata = reader.GetOutput()
        model_points=polydata.GetPoints()
        # #添加一个新的markups节点
        # #markupsNode=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        # index=[7841, 6968, 3089, 8589, 2161, 7462, 2410, 7457, 7692]
        # femur_index = [0, 6, 5, 4, 3, 2, 1, 7, 8]
        # points=[]
        # for i in range(len(femur_index)):
        #     pras=list(model_points.GetPoint(index[femur_index[i]]))
        #     pras[0]=-pras[0]
        #     pras[1]=-pras[1]
        #     points.append(pras)
        #     #markupsNode.AddControlPoint(model_points.GetPoint(i))
        # points.append(points1[-2])
        # points.append(points1[-1])
        # print(points)
        indexOut=[4514, 1278, 6772, 7561, 6347, 9477, 5901, 9764, 6760, 8996, 2811, 7618, 8250, 3802, 9049, 1731, 89, 1922, 6274,
                    4028, 2861, 5867, 6559, 5357, 9055, 9506, 4375, 4375, 2122, 1220, 6344, 8589, 574, 5755, 7045, 2790, 1266, 
                    5311, 5808, 8204, 6886]

        indexInner=[2940, 4251, 7248, 8181, 7196, 3373, 1843, 3614, 8206,
                    8556, 9620, 3115, 2559, 3572, 9758, 5091, 7625, 527,
                    9760, 25, 2846, 1736, 2814, 2161, 1661, 6706, 5196, 7741, 6414, 3073]

        indexFemurUp=[1682, 1500]

        pointsOut=[]
        pointsInner=[]
        for i in indexOut:
            pras=list(model_points.GetPoint(i))
            pras[0]=-pras[0]
            pras[1]=-pras[1]
            pointsOut.append(pras)
        for i in indexInner:
            pras=list(model_points.GetPoint(i))
            pras[0]=-pras[0]
            pras[1]=-pras[1]
            pointsInner.append(pras)
        pointsOut=np.array(pointsOut)
        pointsInner=np.array(pointsInner)

        pointsFemurUp=[]
        for i in indexFemurUp:
            pras=list(model_points.GetPoint(i))
            pras[0]=-pras[0]
            pras[1]=-pras[1]
            pointsFemurUp.append(pras)
        pointsFemurUp=np.array(pointsFemurUp)


        myssm=ssmFemur()
        myssm.FilePath=self.resourcePath("static/asset/ssm")
        myssm.judge=LorR
        myssm.outPutPath=outputPath
        myssm.prparModel(path)
        myssm.preparPointsForFemurGuihua(points,pointsFemurUp)
        myssm.pointsOut=pointsOut.copy()
        myssm.pointsInner=pointsInner.copy()
        myssm.creatCordingnate_femur()
        myssm.SelectJiaTi()
        #世界位置模型旋转90度
        Ftrans1 = np.array([[-1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        RASToUe4 = np.array([[1, 0, 0,0],
                    [0, 0, -1,0],
                    [0, 1, 0,0],
                    [0, 0, 0,1]])
        Ftransx = np.array([[-1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
        RASToUe4 = np.dot(Ftrans1, np.dot(RASToUe4, Ftrans1))
        RASToUe4_ni = np.array([[1, 0, 0,0],
                    [0, 0, 1,0],
                    [0, -1, 0,0],
                    [0, 0, 0,1]])
        
        RASToUe4_ni=np.dot(Ftrans1, np.dot(RASToUe4_ni, Ftrans1))
        # myssm.scaleModel(myssm.FilePath + '/Femur.vtk',0.1,0.1,0.1)
        # myssm.HardModel1(myssm.FilePath + '/Femur.stl',Ftransx)
        myssm.HardModel1(myssm.FilePath + '/Femur111.stl',RASToUe4_ni)
        # myssm.remeshModel(myssm.FilePath + '/Femur.stl')
        myssm.remeshModel(myssm.FilePath + '/Femur111.stl')
        
        FemurPoints = ['开髓点', '内侧凹点', '外侧凸点', '内侧远端', '外侧远端', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点', 'H点', "股骨头球心"]
        # p1=[]
        # for i in range(len(FemurPoints)):
        #     point = myssm.myScene.getMarkupsByName(FemurPoints[i]+"1").getPoints()[0]
        #     points = [point[0], point[1], point[2],1]
        #     points=np.dot(RASToUe4,points)[0:3].tolist()
        #     p1.append(points)

        p=[]
        p1=[]
        #points.append([-10*float(points_x[i]),-10*float(points_z[i]),10*float(points_y[i])])
        for i in range(len(FemurPoints)):
            point = myssm.myScene.getMarkupsByName(FemurPoints[i]).getPoints()[0]
            points = [0.1*point[0], 0.1*point[2], -0.1*point[1]]
            #points = [point[0], point[1], point[2],1]
            p.append(points)
            point = myssm.myScene.getMarkupsByName(FemurPoints[i]+"1").getPoints()[0]
            points = [point[0], point[1], point[2],1]
            points = np.dot(RASToUe4,points)[0:3].tolist()
            p1.append(points)
        trans=[]
        for i in range(8):
            # trans内添加空变换
            trans.append(np.identity(4))


        if LorR=='R':
            np.savetxt(outputPath+'/FemurPoints_R.txt',np.array(p1))
        else:
            np.savetxt(outputPath+'/FemurPoints_L.txt',np.array(p1))


        jiatiload=myssm.jiatiload

        transform=myssm.registion(fromPoints,p1[0:8])
        # 对pointsInner及pointsOut进行变换
        for i in range(len(pointsInner)):
            pointsInner[i]=np.dot(transform,pointsInner[i].tolist()+[1])[0:3]
        for i in range(len(pointsOut)):
            pointsOut[i]=np.dot(transform,pointsOut[i].tolist()+[1])[0:3]

        self.onGenerateLowestPoints(pointsInner,pointsOut)



        return trans,p,p1,jiatiload


    def caculateTibia(self,path,outputPath,points,LorR):
        #path="D:/scala/femur_full_out/tibiaFull.vtk"
        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(path)
        reader.Update()
        polydata = reader.GetOutput()
        model_points=polydata.GetPoints()

        myssm=ssmTibia()
        myssm.FilePath=self.resourcePath("static/asset/ssm")
        myssm.judge=LorR
        myssm.outPutPath=outputPath
        myssm.prparModel(path)
        myssm.preparPointsForTibiaGuihua(points)
        myssm.creatCordingnate_tibia()
        myssm.SelectTibiaJiaTi()
        jiatiload=myssm.jiatiload

        Ftransx = np.array([[-1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
        RASToUe4_ni = np.array([[1, 0, 0,0],
                    [0, 0, 1,0],
                    [0, -1, 0,0],
                    [0, 0, 0,1]])
        Ftrans1 = np.array([[-1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        RASToUe4_ni=np.dot(Ftrans1, np.dot(RASToUe4_ni, Ftrans1))
        myssm.scaleModel(myssm.FilePath + '/Tibia.vtk',0.1,0.1,0.1)
        if LorR=='L':
            myssm.HardModel1(myssm.FilePath + '/Tibia.stl',Ftransx)
        myssm.HardModel1(myssm.FilePath + '/Tibia111.stl',RASToUe4_ni)
        #myssm.remeshModel(myssm.FilePath + '/Tibia.stl')
        myssm.remeshModel(myssm.FilePath + '/Tibia111.stl')
        
        FemurPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
        # p1=[]
        # for i in range(len(FemurPoints)):
        #     point = myssm.myScene.getMarkupsByName(FemurPoints[i]+"1").getPoints()[0]
        #     points = [point[0], point[1], point[2],1]
        #     points=np.dot(RASToUe4,points)[0:3].tolist()
        #     p1.append(points)

        p=[]
        p1=[]
        #points.append([-10*float(points_x[i]),-10*float(points_z[i]),10*float(points_y[i])])
        for i in range(len(FemurPoints)):
            point = myssm.myScene.getMarkupsByName(FemurPoints[i]).getPoints()[0]
            if LorR=='L':
                points = [0.1*point[0], 0.1*point[2], -0.1*point[1]]
            else:
                points = [-0.1*point[0], 0.1*point[2], -0.1*point[1]]
            #points = [point[0], point[1], point[2],1]
            p.append(points)
            point = myssm.myScene.getMarkupsByName(FemurPoints[i]+"1").getPoints()[0]
            if LorR=='L':
                points = [-point[0], point[2], -point[1]]
            else:
                points = [point[0], point[2], -point[1]]
            
            #points=np.dot(RASToUe4,points)[0:3].tolist()
            p1.append(points)
        trans=[]
        for i in range(8):
            # trans内添加空变换
            trans.append(np.identity(4))

        return trans,p,p1,jiatiload



    # 加入骨骼生成及规划方法
    def onGenerateFemur(self):
        """
        当用户点击“生成”按钮时调用。

        该方法调用逻辑类中的生成方法。

        参数:
        无

        返回:
        无
        """




        self.LOrR='R'
        # 为股骨假体创建一个变换矩阵节点
        self.FemurJTTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        self.FemurJTTransNode.SetName('FemurJTTransNode')
        # 添加5个平面节点
        self.FemurPlaneCutNodeList = []
        for i in range(5):
            plane = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode')
            plane.SetCenter(self.planePoits[2][i])
            plane.SetNormal(self.planeNormal[i])
            plane.SetName('FemurPlane'+str(i))
            plane.SetDisplayVisibility(False)
            plane.SetLocked(True)
            plane.SetAndObserveTransformNodeID(self.FemurJTTransNode.GetID())
            self.FemurPlaneCutNodeList.append(plane)
        
        # 从选取的点中，获取最终的点
        pointsName=['开髓点', '内侧凹点', '外侧凸点', '内侧远端区域', '外侧远端区域', '内侧后髁区域', '外侧后髁区域', '外侧皮质高点', 'A点', 'H点']
        # 获取股骨头球心点
        qiuxinPoins = slicer.util.arrayFromMarkupsControlPoints(slicer.util.getNode('股骨头球心'))
        # 球心拟合
        myssm=ssmFemur()
        center=myssm.onGuGuTouConfirm(qiuxinPoins)
        femurPoints = []
        for i in range(len(pointsName)):
            pointNode = slicer.util.getNode(pointsName[i])
            femurPoints.append(list(pointNode.GetNthControlPointPosition(0)))
        femurPoints.append(list(center))
        # 添加区域点
        for i in range(3,8):
            pointNode = slicer.util.getNode(pointsName[i])
            femurPoints+=slicer.util.arrayFromMarkupsControlPoints(pointNode).tolist()
        femurPoints=np.array(femurPoints)
        self.FemurNihe1(femurPoints.copy(), 'R')

        femur_index = [0, 1, 2, 3, 4, 5, 6, 7, 8]
        keypoints = np.array(femurPoints)[femur_index]
        keypoints=list(keypoints)
        keypoints.append(femurPoints[10]) #股骨头球心
        keypoints.append(femurPoints[9]) #H点
        # print(keypoints)
        trans,p,p1,self.FemurJiatiload=self.caculateFemur(self.resourcePath("static/asset/ssm/Femur.vtk"),self.resourcePath("static/asset/ssm/"),np.array(keypoints), 'R')

        # 添加一个新的markups节点
        self.FemurPointsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        self.FemurPointsNode.SetName('FemurPoints')
        for i in range(len(p)):
            self.FemurPointsNode.AddControlPoint(p1[i])
        # 隐藏markupsNode
        self.FemurPointsNode.SetDisplayVisibility(False)
        # 加载假模型
        modelPath=self.resourcePath("static/asset/ssm/Femur111.stl")
        self.FemurModel=slicer.util.loadModel(modelPath)
        self.FemurModel.SetName('FemurModel')
        # self.onHideModel(self.FemurModel, self.viewList[3:6])
        # self.onShowModel(self.FemurModel, self.viewList[0:3])
        self.FemurModel.SetDisplayVisibility(False)
        # 为股骨创建变换矩阵节点
        self.FemurTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        self.FemurTransNode.SetName('FemurTransNode')
        self.FemurModel.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
        self.FemurPointsNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
        self.LowestPointsInnerNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
        self.LowestPointsOutNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
        # 加载股骨假体
        self.onSwitchFemurJTModel(self.FemurJiatiload)



    # # 加入骨骼生成及规划方法
    # def onGenerateFemur(self):
    #     """
    #     当用户点击“生成”按钮时调用。

    #     该方法调用逻辑类中的生成方法。

    #     参数:
    #     无

    #     返回:
    #     无
    #     """
    #     jsonPath = "D:/code/myExt/extension/KneePlane/Resources/static/asset/ssm/FemurR.json"

    #     # # 从选取的点中，获取最终的点
    #     # pointsName=['开髓点', '内侧凹点', '外侧凸点', 'A', '外侧远端区域', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点', 'H点']
    #     # # 获取股骨头球心点
    #     # qiuxinPoins = slicer.util.arrayFromMarkupsControlPoints(slicer.util.getNode('股骨头球心区域'))
    #     # # 球心拟合
    #     # myssm=ssmFemur()
    #     # center=myssm.onGuGuTouConfirm(qiuxinPoins)
        



    #     self.LOrR='R'
    #     # 为股骨假体创建一个变换矩阵节点
    #     self.FemurJTTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
    #     self.FemurJTTransNode.SetName('FemurJTTransNode')
    #     # 添加5个平面节点
    #     self.FemurPlaneCutNodeList = []
    #     for i in range(5):
    #         plane = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode')
    #         plane.SetCenter(self.planePoits[2][i])
    #         plane.SetNormal(self.planeNormal[i])
    #         plane.SetName('FemurPlane'+str(i))
    #         plane.SetDisplayVisibility(False)
    #         plane.SetLocked(True)
    #         plane.SetAndObserveTransformNodeID(self.FemurJTTransNode.GetID())
    #         self.FemurPlaneCutNodeList.append(plane)
        
    #     #读取为字典数据
    #     with open(jsonPath, 'r') as f:
    #         meshPoints = literal_eval(f.read())
    #         points_x=meshPoints['x'].split(',')
    #         points_y=meshPoints['y'].split(',')
    #         points_z=meshPoints['z'].split(',')
    #         points=[]
    #         for i in range(len(points_x)):
    #             if points_x[i]:
    #                 points.append([-10*float(points_x[i]),-10*float(points_z[i]),10*float(points_y[i])])
    #         # for i in range(len(points)):
    #         #     points[i][0]=-points[i][0]
    #         print(points)
    #         #self.FemurNihe1(np.array(points), 'R')
    #         #femur_index = [0, 6, 5, 4, 3, 2, 1, 7, 8,10,9]
    #         femur_index = [0, 1, 2, 3, 4, 5, 6, 7, 8]
    #         keypoints = np.array(points)[femur_index]
    #         keypoints=list(keypoints)
    #         keypoints.append(points[10]) #股骨头球心
    #         keypoints.append(points[9]) #H点
    #         # print(keypoints)
    #         trans,p,p1,self.FemurJiatiload=self.caculateFemur(self.resourcePath("static/asset/ssm/Femur.vtk"),self.resourcePath("static/asset/ssm/"),np.array(keypoints), 'R')

    #         # 添加一个新的markups节点
    #         self.FemurPointsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
    #         self.FemurPointsNode.SetName('FemurPoints')
    #         for i in range(len(p)):
    #             self.FemurPointsNode.AddControlPoint(p1[i])
    #         # 隐藏markupsNode
    #         self.FemurPointsNode.SetDisplayVisibility(False)
    #         # 加载假模型
    #         modelPath=self.resourcePath("static/asset/ssm/Femur111.stl")
    #         self.FemurModel=slicer.util.loadModel(modelPath)
    #         self.FemurModel.SetName('FemurModel')
    #         # self.onHideModel(self.FemurModel, self.viewList[3:6])
    #         # self.onShowModel(self.FemurModel, self.viewList[0:3])
    #         self.FemurModel.SetDisplayVisibility(False)
    #         # 为股骨创建变换矩阵节点
    #         self.FemurTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
    #         self.FemurTransNode.SetName('FemurTransNode')
    #         self.FemurModel.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
    #         self.FemurPointsNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
    #         self.LowestPointsInnerNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
    #         self.LowestPointsOutNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
    #         # 加载股骨假体
    #         self.onSwitchFemurJTModel(self.FemurJiatiload)

    

    def onGenerateTibia(self):
        """
        当用户点击“生成”按钮时调用。

        该方法调用逻辑类中的生成方法。

        参数:
        无

        返回:
        无
        """
        self.LOrR='R'
        # 为胫骨假体创建一个变换矩阵节点
        self.TibiaJTTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        self.TibiaJTTransNode.SetName('TibiaJTTransNode')
        # 添加1个平面节点
        self.TibiaPlaneCutNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode')
        self.TibiaPlaneCutNode.SetCenter(0,0,0)
        self.TibiaPlaneCutNode.SetNormal(0,0,-1)
        self.TibiaPlaneCutNode.SetName('TibiaPlane')
        self.TibiaPlaneCutNode.SetDisplayVisibility(False)
        self.TibiaPlaneCutNode.SetLocked(True)
        self.TibiaPlaneCutNode.SetAndObserveTransformNodeID(self.TibiaJTTransNode.GetID())

        # 从选取的点中，获取最终的点
        pointsName=['胫骨隆凸', '胫骨内侧区域', '胫骨外侧区域', '内侧边缘','外侧边缘','胫骨结节区域','结节上侧边缘','结节内侧边缘', '结节外侧边缘','内踝点','外踝点']
        # 求踝穴中心
        tibiaPoints = []
        for i in range(len(pointsName)):
            pointNode = slicer.util.getNode(pointsName[i])
            tibiaPoints.append(list(pointNode.GetNthControlPointPosition(0)))
        # 添加区域点
        for name in ['胫骨内侧区域','胫骨外侧区域', '胫骨结节区域']:
            pointNode = slicer.util.getNode(name)
            tibiaPoints+=slicer.util.arrayFromMarkupsControlPoints(pointNode).tolist()
        tibiaPoints=np.array(tibiaPoints)

        self.TibiaNihe(np.array(tibiaPoints), 'R')
        femur_index = [0, 1, 2, 3, 4, 5, 6, 7, 8,9,10,11]
        keypoints = np.array(tibiaPoints)[femur_index]
        # print(keypoints)
        trans,p,p1,jiatiload=self.caculateTibia(self.resourcePath("static/asset/ssm/Tibia.vtk"),self.resourcePath("static/asset/ssm/"),np.array(keypoints), 'R')
        print(p1,jiatiload)

        # 添加一个新的markups节点
        self.TibiaPointsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        self.TibiaPointsNode.SetName('TibiaPoints')
        for i in range(len(p1)):
            self.TibiaPointsNode.AddControlPoint(p1[i])
        # 隐藏markupsNode
        self.TibiaPointsNode.SetDisplayVisibility(False)
        # 加载假模型
        modelPath=self.resourcePath("static/asset/ssm/Tibia111.stl")
        self.TibiaModel=slicer.util.loadModel(modelPath)
        self.TibiaModel.SetName('TibiaModel')
        # self.onHideModel(self.TibiaModel, self.viewList[3:6])
        # self.onShowModel(self.TibiaModel, self.viewList[0:3])
        self.TibiaModel.SetDisplayVisibility(False)
        # 为胫骨创建变换矩阵节点
        self.TibiaTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
        self.TibiaTransNode.SetName('TibiaTransNode')
        self.TibiaModel.SetAndObserveTransformNodeID(self.TibiaTransNode.GetID())
        self.TibiaPointsNode.SetAndObserveTransformNodeID(self.TibiaTransNode.GetID())
        # 加载胫骨假体
        self.onSwitchTibiaJTModel(jiatiload)

    # def onGenerateTibia(self):
    #     """
    #     当用户点击“生成”按钮时调用。

    #     该方法调用逻辑类中的生成方法。

    #     参数:
    #     无

    #     返回:
    #     无
    #     """
    #     jsonPath = "D:/code/myExt/extension/KneePlane/Resources/static/asset/ssm/TibiaR.json"
    #     self.LOrR='R'
    #     # 为胫骨假体创建一个变换矩阵节点
    #     self.TibiaJTTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
    #     self.TibiaJTTransNode.SetName('TibiaJTTransNode')
    #     # 添加1个平面节点
    #     self.TibiaPlaneCutNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode')
    #     self.TibiaPlaneCutNode.SetCenter(0,0,0)
    #     self.TibiaPlaneCutNode.SetNormal(0,0,-1)
    #     self.TibiaPlaneCutNode.SetName('TibiaPlane')
    #     self.TibiaPlaneCutNode.SetDisplayVisibility(False)
    #     self.TibiaPlaneCutNode.SetLocked(True)
    #     self.TibiaPlaneCutNode.SetAndObserveTransformNodeID(self.TibiaJTTransNode.GetID())

    
    #     #读取为字典数据
    #     with open(jsonPath, 'r') as f:
    #         meshPoints = literal_eval(f.read())
    #         points_x=meshPoints['x'].split(',')
    #         points_y=meshPoints['y'].split(',')
    #         points_z=meshPoints['z'].split(',')
    #         points=[]
    #         for i in range(len(points_x)):
    #             if points_x[i]:
    #                 points.append([-10*float(points_x[i]),-10*float(points_z[i]),10*float(points_y[i])])
    #         for i in range(len(points)):
    #             points[i][0]=-points[i][0]
    #         print(points)
    #         #self.TibiaNihe(np.array(points), 'R')
    #         femur_index = [0, 1, 2, 3, 4, 5, 6, 7, 8,9,10,11,12,13,14]
    #         keypoints = np.array(points)[femur_index]
    #         # print(keypoints)
    #         trans,p,p1,jiatiload=self.caculateTibia(self.resourcePath("static/asset/ssm/Tibia.vtk"),self.resourcePath("static/asset/ssm/"),np.array(keypoints), 'R')
    #         print(p1,jiatiload)

    #         # 添加一个新的markups节点
    #         self.TibiaPointsNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
    #         self.TibiaPointsNode.SetName('TibiaPoints')
    #         for i in range(len(p1)):
    #             self.TibiaPointsNode.AddControlPoint(p1[i])
    #         # 隐藏markupsNode
    #         self.TibiaPointsNode.SetDisplayVisibility(False)
    #         # 加载假模型
    #         modelPath=self.resourcePath("static/asset/ssm/Tibia111.stl")
    #         self.TibiaModel=slicer.util.loadModel(modelPath)
    #         self.TibiaModel.SetName('TibiaModel')
    #         # self.onHideModel(self.TibiaModel, self.viewList[3:6])
    #         # self.onShowModel(self.TibiaModel, self.viewList[0:3])
    #         self.TibiaModel.SetDisplayVisibility(False)
    #         # 为胫骨创建变换矩阵节点
    #         self.TibiaTransNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode')
    #         self.TibiaTransNode.SetName('TibiaTransNode')
    #         self.TibiaModel.SetAndObserveTransformNodeID(self.TibiaTransNode.GetID())
    #         self.TibiaPointsNode.SetAndObserveTransformNodeID(self.TibiaTransNode.GetID())
    #         # 加载胫骨假体
    #         self.onSwitchTibiaJTModel(jiatiload)

    # 生成最低点点列
    def onGenerateLowestPoints(self,inners=[],outs=[]):


        # 创建一个新的markups节点
        self.LowestPointsInnerNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        self.LowestPointsInnerNode.SetName('LowestPointsInner')
        for i in inners:
            self.LowestPointsInnerNode.AddControlPoint(i)

        self.LowestPointsOutNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        self.LowestPointsOutNode.SetName('LowestPointsOuter')
        for i in outs:
            self.LowestPointsOutNode.AddControlPoint(i)
        
        # 隐藏markupsNode
        self.LowestPointsInnerNode.SetDisplayVisibility(False)
        self.LowestPointsOutNode.SetDisplayVisibility(False)

        # # 设置父级
        # self.LowestPointsInnerNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())
        # self.LowestPointsOutNode.SetAndObserveTransformNodeID(self.FemurTransNode.GetID())

    # 获取最低点
    def getLowestPoints(self):
        # 获取最低点
        innerPoints = []
        for i in range(self.LowestPointsInnerNode.GetNumberOfControlPoints()):
            innerPoints.append(np.array(self.LowestPointsInnerNode.GetNthControlPointPositionWorld(i)))
        outPoints = []
        for i in range(self.LowestPointsOutNode.GetNumberOfControlPoints()):
            outPoints.append(np.array(self.LowestPointsOutNode.GetNthControlPointPositionWorld(i)))
        # 获取Z轴最小值所在点
        innerPoints = np.array(innerPoints)
        outPoints = np.array(outPoints)
        innerMinIndex = np.argmin(innerPoints[:,2])
        outMinIndex = np.argmin(outPoints[:,2])
        return innerPoints[innerMinIndex], outPoints[outMinIndex]


            
    # 变换矩阵转欧拉角
    def transToEuler(self, trans):
        # 提取旋转矩阵部分
        R = trans[:3, :3]

        # 计算欧拉角
        sy = sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
        singular = sy < 1e-6

        if not singular:
            x = atan2(R[2, 1], R[2, 2])
            y = atan2(-R[2, 0], sy)
            z = atan2(R[1, 0], R[0, 0])
        else:
            x = atan2(-R[1, 2], R[1, 1])
            y = atan2(-R[2, 0], sy)
            z = 0

        # 将弧度转换为角度
        return np.degrees(np.array([x, y, z]))

    def eulerToTrans(self, euler_angles,position):
        # 将角度转换为弧度
        euler_angles = np.radians(euler_angles)
        x, y, z = euler_angles

        # 计算旋转矩阵
        Rx = np.array([
            [1, 0, 0],
            [0, cos(x), -sin(x)],
            [0, sin(x), cos(x)]
        ])

        Ry = np.array([
            [cos(y), 0, sin(y)],
            [0, 1, 0],
            [-sin(y), 0, cos(y)]
        ])

        Rz = np.array([
            [cos(z), -sin(z), 0],
            [sin(z), cos(z), 0],
            [0, 0, 1]
        ])

        # 组合旋转矩阵
        R = Rz @ Ry @ Rx

        # 创建4x4变换矩阵
        trans = np.eye(4)
        trans[:3, :3] = R
        # 设置平移部分
        trans[:3, 3] = position

        return trans

    # 对变换矩阵进行调整
    def adjustTrans(self,transNode, euler_angles, position):
        # 获取变换矩阵数组
        transArray = slicer.util.arrayFromTransformMatrix(transNode)
        # 将变换矩阵转换为欧拉角
        current_euler_angles = self.transToEuler(transArray)
        # 计算新的欧拉角
        new_euler_angles = current_euler_angles + euler_angles
        # 将新的欧拉角转换为变换矩阵
        new_transArray = self.eulerToTrans(new_euler_angles, position+transArray[:3,3])
        # 将新的变换矩阵设置到变换节点中
        transNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(new_transArray))

    def onFemurXMove1(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, 0], [1, 0, 0])
        self.onCropFemur()
    
    def onFemurXMove2(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, 0], [-1, 0, 0])
        self.onCropFemur()
    
    def onFemurYMove1(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, 0], [0, 1, 0])
        self.onCropFemur()

    def onFemurYMove2(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, 0], [0, -1, 0])
        self.onCropFemur()

    def onFemurZMove1(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, 0], [0, 0, 1])
        self.onCropFemur()

    def onFemurZMove2(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, 0], [0, 0, -1])
        self.onCropFemur()

    def onFemurRotateX1(self):
        self.adjustTrans(self.FemurTransNode, [1, 0, 0], [0, 0, 0])
        self.onCropFemur()

    def onFemurRotateX2(self):
        self.adjustTrans(self.FemurTransNode, [-1, 0, 0], [0, 0, 0])
        self.onCropFemur()

    def onFemurRotateY1(self):
        self.adjustTrans(self.FemurTransNode, [0, 1, 0], [0, 0, 0])
        self.onCropFemur()


    def onFemurRotateY2(self):
        self.adjustTrans(self.FemurTransNode, [0, -1, 0], [0, 0, 0])
        self.onCropFemur()

    def onFemurRotateZ1(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, 1], [0, 0, 0])
        self.onCropFemur()

    def onFemurRotateZ2(self):
        self.adjustTrans(self.FemurTransNode, [0, 0, -1], [0, 0, 0])
        self.onCropFemur()

    def onTibiaXMove1(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, 0], [1, 0, 0])
        self.onCropTibia()

    def onTibiaXMove2(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, 0], [-1, 0, 0])
        self.onCropTibia()

    def onTibiaYMove1(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, 0], [0, 1, 0])
        self.onCropTibia()

    def onTibiaYMove2(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, 0], [0, -1, 0])
        self.onCropTibia()

    def onTibiaZMove1(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, 0], [0, 0, 1])
        self.onCropTibia()

    def onTibiaZMove2(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, 0], [0, 0, -1])
        self.onCropTibia()

    def onTibiaRotateX1(self):
        self.adjustTrans(self.TibiaTransNode, [1, 0, 0], [0, 0, 0])
        self.onCropTibia()

    def onTibiaRotateX2(self):
        self.adjustTrans(self.TibiaTransNode, [-1, 0, 0], [0, 0, 0])
        self.onCropTibia()

    def onTibiaRotateY1(self):
        self.adjustTrans(self.TibiaTransNode, [0, 1, 0], [0, 0, 0])
        self.onCropTibia()

    def onTibiaRotateY2(self):
        self.adjustTrans(self.TibiaTransNode, [0, -1, 0], [0, 0, 0])
        self.onCropTibia()

    def onTibiaRotateZ1(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, 1], [0, 0, 0])
        self.onCropTibia()

    def onTibiaRotateZ2(self):
        self.adjustTrans(self.TibiaTransNode, [0, 0, -1], [0, 0, 0])
        self.onCropTibia()






    # 对股骨进行裁剪
    def onCropFemur(self):
        # 判断输出结果模型是否存在
        if not self.FemurCropModel:
            # 创建一个新的模型节点
            self.FemurCropModel = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
            self.FemurCropModel.SetName('FemurCropModel')
            self.FemurCropModel.CreateDefaultDisplayNodes()
            self.FemurCropModel.GetDisplayNode().SetColor(1, 1, 0)
            self.FemurCropModel.GetDisplayNode().SetVisibility(1)
            # 将模型节点添加到场景中
            slicer.mrmlScene.AddNode(self.FemurCropModel)
            self.FemurDynamicModelerNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLDynamicModelerNode")
            self.FemurDynamicModelerNode.SetToolName("Plane cut")
            self.FemurDynamicModelerNode.SetNodeReferenceID("PlaneCut.InputModel", self.FemurModel.GetID())
            # 设置切割平面
            for i in range(5):
                self.FemurDynamicModelerNode.AddNodeReferenceID("PlaneCut.InputPlane", self.FemurPlaneCutNodeList[i].GetID())
            # 设置输出模型
            self.FemurDynamicModelerNode.SetNodeReferenceID("PlaneCut.OutputPositiveModel", self.FemurCropModel.GetID())
            slicer.modules.dynamicmodeler.logic().RunDynamicModelerTool(self.FemurDynamicModelerNode)
            # 设置模型在哪几个视图中显示
            self.onShowModel(self.FemurCropModel, [self.viewList[0],self.viewList[1],self.viewList[2],self.viewList[4]])
            self.onHideModel(self.FemurCropModel, [self.viewList[3],self.viewList[5]])

        else:
            slicer.modules.dynamicmodeler.logic().RunDynamicModelerTool(self.FemurDynamicModelerNode)
        
        self.onCalculate()

    # 对胫骨进行裁剪
    def onCropTibia(self):
        # 判断输出结果模型是否存在
        if not self.TibiaCropModel:
            # 创建一个新的模型节点
            self.TibiaCropModel = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
            self.TibiaCropModel.SetName('TibiaCropModel')
            self.TibiaCropModel.CreateDefaultDisplayNodes()
            self.TibiaCropModel.GetDisplayNode().SetColor(1, 1, 0)
            self.TibiaCropModel.GetDisplayNode().SetVisibility(1)
            # 将模型节点添加到场景中
            slicer.mrmlScene.AddNode(self.TibiaCropModel)
            self.TibiaDynamicModelerNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLDynamicModelerNode")
            self.TibiaDynamicModelerNode.SetToolName("Plane cut")
            self.TibiaDynamicModelerNode.SetNodeReferenceID("PlaneCut.InputModel", self.TibiaModel.GetID())
            # 设置切割平面
            self.TibiaDynamicModelerNode.AddNodeReferenceID("PlaneCut.InputPlane", self.TibiaPlaneCutNode.GetID())
            # 设置输出模型
            self.TibiaDynamicModelerNode.SetNodeReferenceID("PlaneCut.OutputPositiveModel", self.TibiaCropModel.GetID())
            slicer.modules.dynamicmodeler.logic().RunDynamicModelerTool(self.TibiaDynamicModelerNode)
            # 设置模型在哪几个视图中显示
            self.onShowModel(self.TibiaCropModel, self.viewList[3:6])
            self.onHideModel(self.TibiaCropModel, self.viewList[0:3])

        else:
            slicer.modules.dynamicmodeler.logic().RunDynamicModelerTool(self.TibiaDynamicModelerNode)

        self.onCalculate()


    # 计算各角度及距离信息
    def onCalculate(self):
        # 计算股骨内侧截骨间距
        # 获取股骨第一刀截骨面
        plane1 = self.FemurPlaneCutNodeList[0]
        plane1Normal = np.array(plane1.GetNormalWorld())
        plane1Center = np.array(plane1.GetCenterWorld())
        # 获取内侧远端点
        point1 = np.array(self.FemurPointsNode.GetNthControlPointPositionWorld(3))
        # 计算内侧远端点到第一刀截骨面的距离
        distance1 = np.abs(np.dot(plane1Normal, point1 - plane1Center))
        if (self.onCalculatePointWithPlane(point1, plane1Center, plane1Normal)):
            distance1 = -distance1
        # 计算股骨外侧截骨间距
        # 获取外侧远端点
        point2 = np.array(self.FemurPointsNode.GetNthControlPointPositionWorld(4))
        # 计算外侧远端点到第一刀截骨面的距离
        distance2 = np.abs(np.dot(plane1Normal, point2 - plane1Center))
        if (self.onCalculatePointWithPlane(point2, plane1Center, plane1Normal)):
            distance2 = -distance2
        # 计算股骨内侧后髁间距
        # 获取内侧后髁点
        point3 = np.array(self.FemurPointsNode.GetNthControlPointPositionWorld(5))
        # 获取股骨第三刀截骨面
        plane3 = self.FemurPlaneCutNodeList[2]
        plane3Normal = np.array(plane3.GetNormalWorld())
        plane3Center = np.array(plane3.GetCenterWorld())
        # 计算内侧后髁点到第三刀截骨面的距离
        distance3 = np.abs(np.dot(plane3Normal, point3 - plane3Center))
        if (self.onCalculatePointWithPlane(point3, plane3Center, plane3Normal)):
            distance3 = -distance3
        # 计算股骨外侧后髁间距
        # 获取外侧后髁点
        point4 = np.array(self.FemurPointsNode.GetNthControlPointPositionWorld(6))
        # 计算外侧后髁点到第三刀截骨面的距禿
        distance4 = np.abs(np.dot(plane3Normal, point4 - plane3Center))
        if (self.onCalculatePointWithPlane(point4, plane3Center, plane3Normal)):
            distance4 = -distance4
        # 计算股骨外侧皮质高点间距
        # 获取外侧皮质高点
        point5 = np.array(self.FemurPointsNode.GetNthControlPointPositionWorld(7))
        # 获取第二刀截骨面
        plane2 = self.FemurPlaneCutNodeList[1]
        plane2Normal = np.array(plane2.GetNormalWorld())
        plane2Center = np.array(plane2.GetCenterWorld())
        # 计算外侧皮质高点到第二刀截骨面的距离
        distance5 = np.abs(np.dot(plane2Normal, point5 - plane2Center))
        if (self.onCalculatePointWithPlane(point5, plane2Center, plane2Normal)):
            distance5 = -distance5



        # 计算假体变换矩阵到股骨变换矩阵的变换
        femurTrans = slicer.util.arrayFromTransformMatrix(self.FemurTransNode)
        femurJTTrans = slicer.util.arrayFromTransformMatrix(self.FemurJTTransNode)
        femurJTTransToTrans = np.dot(femurTrans,np.linalg.inv(femurJTTrans))
        femurJTTransToTransEuler = self.transToEuler(femurJTTransToTrans)
        print("外侧截骨间距：", distance2)
        print("内侧截骨间距：", distance1)
        print("内侧后髁间距：", distance3)
        print("外侧后髁间距：", distance4)
        print("外侧皮质高点间距：", distance5)
        print("假体变换矩阵到股骨变换矩阵角度：", femurJTTransToTransEuler)

        self.viewButtonList[0].setCenterText(-femurJTTransToTransEuler[1])
        self.viewButtonList[1].setLeftText(distance2)
        self.viewButtonList[1].setRightText(distance1)
        self.viewButtonList[2].setCenterText(femurJTTransToTransEuler[2])
        self.viewButtonList[3].setLeftText(distance4)
        self.viewButtonList[3].setRightText(distance3)
        self.viewButtonList[4].setCenterText(-femurJTTransToTransEuler[0])
        self.viewButtonList[5].setCenterText(distance5)




        try:
            # 获取胫骨切割面
            plane = self.TibiaPlaneCutNode
            planeNormal = np.array(plane.GetNormalWorld())
            planeCenter = np.array(plane.GetCenterWorld())
            # 获取胫骨内侧高点
            point1 = np.array(self.TibiaPointsNode.GetNthControlPointPositionWorld(0))
            # 计算内侧高点到切割面的距离
            distance1 = np.abs(np.dot(planeNormal, point1 - planeCenter))
            if (self.onCalculatePointWithPlane(point1, planeCenter, planeNormal)):
                distance1 = -distance1
            # 获取胫骨外侧高点
            point2 = np.array(self.TibiaPointsNode.GetNthControlPointPositionWorld(1))
            # 计算外侧高点到切割面的距离
            distance2 = np.abs(np.dot(planeNormal, point2 - planeCenter))
            if (self.onCalculatePointWithPlane(point2, planeCenter, planeNormal)):
                distance2 = -distance2

            #   计算胫骨假体变换矩阵到股骨变换矩阵的变换
            tibiaTrans = slicer.util.arrayFromTransformMatrix(self.TibiaTransNode)
            tibiaJTTrans = slicer.util.arrayFromTransformMatrix(self.TibiaJTTransNode)
            tibiaJTTransToTrans = np.dot(tibiaTrans,np.linalg.inv(tibiaJTTrans))
            tibiaJTTransToTransEuler = self.transToEuler(tibiaJTTransToTrans)

            self.viewButtonList[6].setLeftText(distance1)
            self.viewButtonList[6].setRightText(distance2)
            self.viewButtonList[7].setCenterText(-tibiaJTTransToTransEuler[1])
            self.viewButtonList[8].setCenterText(-tibiaJTTransToTransEuler[0])

        except Exception as e:
            print(e)

        
    # 计算一个点在平面的正面还是背面
    def onCalculatePointWithPlane(self, point, planeCenter, planeNormal):
        # 计算点到平面中心的向量
        vector = [point[i] - planeCenter[i] for i in range(3)]
        
        # 计算向量与平面法向量的点积
        dot_product = sum(vector[i] * planeNormal[i] for i in range(3))
        
        # 根据点积的符号判断点在平面的正面还是背面
        if dot_product > 0:
            return 1
        else:
            return 0

    # 根据型号切换假体
    def onSwitchFemurJTModel(self,index):
        JTList = ['1-5', '2', '2-5', '3', '4', '5']
        size = JTList[index]
        if (self.LOrR=='R'):
            jtName = 'femur-R' + size+".stl"
        else:
            jtName = 'femur-L' + size+".stl"
        jtPath = self.resourcePath("static/asset/ssm/假体库/新建文件夹/"+jtName)
        self.FemurJtModel = slicer.util.loadModel(jtPath)
        self.FemurJtModel.SetAndObserveTransformNodeID(self.FemurJTTransNode.GetID())
        self.onHideModel(self.FemurJtModel, [self.viewList[3],self.viewList[5]])
        self.onShowModel(self.FemurJtModel, [self.viewList[0],self.viewList[1],self.viewList[2],self.viewList[4]])
        # 更新切割平面的位置
        for i in range(5):
            self.FemurPlaneCutNodeList[i].SetCenter(self.planePoits[index][i])
            self.FemurPlaneCutNodeList[i].SetNormal(self.planeNormal[i])
        # 切割一下
        self.onCropFemur()
        slicer.modules.surgical_navigation.widgetRepresentation()
        slicer.modules.surgical_navigation.widgetRepresentation().self().onChangeJTFemur(self.FemurJtModel)


    # 根据型号切换假体
    def onSwitchTibiaJTModel(self,index):
        JTList = ['1-5', '2', '2-5', '3', '4', '5']
        size = JTList[index]

        jtName = 'Tibia-' + size+".stl"
        jtPath = self.resourcePath("static/asset/ssm/假体库/新建文件夹/"+jtName)
        insertPath = self.resourcePath("static/asset/ssm/假体库/新建文件夹/insert-"+size+".stl")
        self.TibiaJtModel = slicer.util.loadModel(jtPath)
        self.TibiaJtModel.SetAndObserveTransformNodeID(self.TibiaJTTransNode.GetID())
        self.insertModel = slicer.util.loadModel(insertPath)
        self.insertModel.SetAndObserveTransformNodeID(self.TibiaJTTransNode.GetID())
        self.onHideModel(self.TibiaJtModel, self.viewList[0:3])
        self.onShowModel(self.TibiaJtModel, self.viewList[3:6])
        self.onHideModel(self.insertModel, self.viewList[0:3])
        self.onHideModel(self.insertModel, [self.viewList[3],self.viewList[5]])
        self.onShowModel(self.insertModel, [self.viewList[4]])

        # 切割一下
        self.onCropTibia()
        slicer.modules.surgical_navigation.widgetRepresentation().self().onChangeJTTibia(self.TibiaJtModel)



    # 设置模型在哪几个视图中显示
    def onShowModel(self, model, viewListShow):
        for view in viewListShow:
            model.GetDisplayNode().AddViewNodeID(view.mrmlViewNode().GetID())

    # 设置模型在哪几个视图中隐藏
    def onHideModel(self, model, viewListHide):
        for view in viewListHide:
            model.GetDisplayNode().RemoveViewNodeID(view.mrmlViewNode().GetID())


    # 设置相机位置
    def onSetUpCameraPostion(self):
        # 设置相机位置
        cameraNode1 = self.viewList[0].viewWidget().cameraNode()
        cameraNode1.SetPosition(-10,220,86)
        cameraNode1.SetFocalPoint(-0.33849105053600015, -14.105985454633185, 37.82753606832123)
        cameraNode1.SetViewUp(0,0,1)

        cameraNode2 = self.viewList[1].viewWidget().cameraNode()
        cameraNode2.SetPosition(-0.15139438686509582, 18.875652817991504, -209.91391457446187)
        cameraNode2.SetFocalPoint(-1.15139559541511, -9.583986096719684, 39.541818735187434)
        cameraNode2.SetViewUp(0,1,0)

        cameraNode3 = self.viewList[2].viewWidget().cameraNode()
        cameraNode3.SetPosition(-218.23854305223483, 20.10870251055027, 51.01192064219559)
        cameraNode3.SetFocalPoint(11.175099901607846, -5.387375179170135, 37.5249394544531)
        cameraNode3.SetViewUp(0,0,1)


        cameraNode4 = self.viewList[3].viewWidget().cameraNode()
        cameraNode4.SetPosition(-1.7763419224401735, 220, 5.23579573255438)
        cameraNode4.SetFocalPoint(-1.004804831082927, -26.021214255175835, -35.354058258038364)
        cameraNode4.SetViewUp(0,0,1)

        cameraNode5 = self.viewList[4].viewWidget().cameraNode()
        cameraNode5.SetPosition(0, 251, 0)
        cameraNode5.SetFocalPoint(0,0,0)
        cameraNode5.SetViewUp(0,0,1)

        cameraNode6 = self.viewList[5].viewWidget().cameraNode()
        cameraNode6.SetPosition(-218.356196923346, -1.2389955484864166, 7.833524620360268)
        cameraNode6.SetFocalPoint(-14.356235176495346, -0.6449887835159274, -30.116782257890414)
        cameraNode6.SetViewUp(0,0,1)
        for i in range(6):
            self.viewList[i].viewWidget().resetFocalPoint()









class CustomWindow(qt.QWidget):
    def __init__(self):
        super().__init__()
    def resizeEvent(self, event):
        slicer.modules.kneeplane.widgetRepresentation().self().updatePopWidgetPosition1()

# 自定义Label,包含两个label,两个label包含不同内容，一个是数字，一个是单位，数字设置特殊大小，单位设置右下对齐
class CustomLabel(qt.QLabel):
    def __init__(self, number_text = '', unit_text = '', parent=None):
        super().__init__(parent)
        self.number_label = qt.QLabel(number_text, self)
        self.unit_label = qt.QLabel(unit_text, self)
        self.initUI()

    def initUI(self):
        layout = qt.QHBoxLayout(self)
        layout.addWidget(self.number_label)
        #layout.addStretch()
        layout.addWidget(self.unit_label)
        layout.setSpacing(0)
        self.setLayout(layout)
        # 设置右对齐
        self.number_label.setAlignment(qt.Qt.AlignRight | qt.Qt.AlignBottom)
        self.unit_label.setAlignment(qt.Qt.AlignLeft | qt.Qt.AlignBottom)
        #文本颜色为白色
        self.number_label.setStyleSheet("font-size: 24px;color: white;")
        self.unit_label.setStyleSheet("color: white;")
        

    def setNumbers(self, number_text):
        self.number_label.setText(number_text)

    def setText(self, text):
        self.unit_label.setText(text)

    def setAlignment_num(self, alignment):
        self.number_label.setAlignment(alignment)

    def setAlignment_unit(self, alignment):
        self.unit_label.setAlignment(alignment)


class CustomButton_two(qt.QPushButton):
    def __init__(self, left_text='', right_text='', parent=None):
        super().__init__(parent)
        self.number_left = 0
        self.number_right = 0
        # self.left_label = qt.QLabel(left_text, self)
        # self.right_label = qt.QLabel(right_text, self)
        self.left_label = CustomLabel(self.number_left, left_text, self)
        self.right_label = CustomLabel(self.number_right, right_text, self)
        self.initUI()

    
    def initUI(self):
        layout = qt.QHBoxLayout(self)
        layout.addWidget(self.left_label)
        #layout.addStretch()
        layout.addWidget(self.right_label)
        self.setLayout(layout)

        # 设置Margin为0
        #self.layout().setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)       

    def setLeftText(self, text):
        self.left_label.setText(text)

    def setRightText(self, text):
        self.right_label.setText(text)

    def setLeftNumber(self, number):
        self.number_left = number
        self.left_label.setNumbers(number)

    def setRightNumber(self, number):
        self.number_right = number
        self.right_label.setNumbers(number)

class CustomButton_one(qt.QPushButton):
    def __init__(self, center_text='', parent=None):
        super().__init__(parent)
        # self.left_label = qt.QLabel(left_text, self)
        # self.right_label = qt.QLabel(right_text, self)
        self.center_number = 0
        self.center_text_label = CustomLabel(self.center_number, center_text, self)
        self.initUI()
        
    def initUI(self):
        layout = qt.QHBoxLayout(self)
        layout.addWidget(self.center_text_label)
        #layout.addStretch()
        self.setLayout(layout)

        # 设置Margin为0
        # self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)
    

    def setCenterNumber(self, number):
        self.center_number = number
        self.center_text_label.setNumbers(number)

    def setCenterText(self, text):
        self.center_text_label.setText(text)


class ViewPopWidget1(qt.QWidget):
    def __init__(self, type):
        super().__init__()
        self.type = type
        self.initUI()
        self.initAnimations()

    def initUI(self):
        # 创建布局
        layout = qt.QHBoxLayout()
        self.setMaximumWidth(320)
        self.setMaximumHeight(60)

        # 创建并添加-按钮
        self.LeftButton = qt.QPushButton('-', self)
        layout.addWidget(self.LeftButton)
        # 设置最大宽度
        self.LeftButton.setMaximumWidth(50)
        # 设置最小高度
        self.LeftButton.setMinimumHeight(50)
        self.LeftButton.hide()

        if self.type == 1:
            self.CenterButton = CustomButton_one('度', self)
            self.CenterButton.setMaximumWidth(120)
            self.CenterButton.setMinimumWidth(120)
            self.setMaximumWidth(223)
        else:
            self.CenterButton = CustomButton_two('毫米', '毫米', self)
            self.CenterButton.setMaximumWidth(200)
            self.CenterButton.setMinimumWidth(200)


        self.CenterButton.setMinimumHeight(50)
        layout.addWidget(self.CenterButton)
        self.CenterButton.clicked.connect(self.onCenterClick)
        self.CenterButton.setCheckable(True)

        # 创建并添加+按钮
        self.RightButton = qt.QPushButton('+', self)
        layout.addWidget(self.RightButton)
        self.RightButton.setMaximumWidth(50)
        self.RightButton.setMinimumHeight(50)
        self.RightButton.hide()

        # 设置布局
        self.setLayout(layout)
        # 设置窗口无边框
        self.setWindowFlags(qt.Qt.FramelessWindowHint)
        # 设置窗口透明
        self.setAttribute(qt.Qt.WA_TranslucentBackground)
        button_style = """
        QPushButton {
            background-color: transparent;
            border: 2px solid lightgray;
            color: white;
            border-radius: 20px;
        }
        QPushButton:checked {
            background-color: rgba(255, 255, 255, 30);
        }
        QPushButton:pressed {
            background-color: rgba(255, 255, 255, 50);
        }
        """

        self.LeftButton.setStyleSheet(button_style)
        self.CenterButton.setStyleSheet(button_style)
        self.RightButton.setStyleSheet(button_style)
        

    def initAnimations(self):
        self.left_animation = qt.QPropertyAnimation(self.LeftButton, b"pos")
        self.right_animation = qt.QPropertyAnimation(self.RightButton, b"pos")

        self.left_animation.setDuration(300)
        self.right_animation.setDuration(300)
        # 结束后隐藏按钮
        self.left_animation.finished.connect(self.setButtonVisible)
        self.right_animation.finished.connect(self.setButtonVisible)



    def onCenterClick(self):
        center_button_width = self.CenterButton.width
        left_button_width = self.LeftButton.width
        right_button_width = self.RightButton.width

        if self.CenterButton.isChecked():
            self.LeftButton.show()
            self.RightButton.show()

            # 计算中间按钮的中心位置
            center_pos = self.CenterButton.pos + qt.QPoint(center_button_width // 2, 0)
            
            # 计算左右侧按钮的起始位置，使它们位于中间按钮的两端
            left_start_pos = center_pos
            right_start_pos = center_pos

            # 计算左右侧按钮的结束位置，最终位置距离中间按钮3个像素
            left_end_pos = qt.QPoint(6, 6)#center_pos - qt.QPoint(center_button_width // 2 + 3+left_button_width, 0)
            right_end_pos = center_pos + qt.QPoint(center_button_width // 2 + 3, 0)
            left_start_pos=left_end_pos+qt.QPoint(left_button_width+3,0)
            right_start_pos=right_end_pos-qt.QPoint(right_button_width+3,0)


            self.left_animation.setStartValue(left_start_pos)
            self.left_animation.setEndValue(left_end_pos)

            self.right_animation.setStartValue(right_start_pos)
            self.right_animation.setEndValue(right_end_pos)

            # 确保中间按钮在最上层
            self.CenterButton.raise_()

            # 启动动画
            self.left_animation.start()
            self.right_animation.start()
        else:
            # 计算中间按钮的中心位置
            center_pos = self.CenterButton.pos + qt.QPoint(center_button_width // 2, 0)
            
            # 计算左右侧按钮的起始位置，使它们位于中间按钮的两端
            left_start_pos = qt.QPoint(6, 6)#center_pos - qt.QPoint(center_button_width // 2 + 3+left_button_width, 0)
            right_start_pos = center_pos + qt.QPoint(center_button_width // 2 + 3, 0)

            # 计算左右侧按钮的结束位置，最终位置为中间按钮的中心位置
            left_end_pos = left_start_pos+qt.QPoint(left_button_width+3,0) 
            right_end_pos = right_start_pos-qt.QPoint(right_button_width+3,0)


            self.left_animation.setStartValue(left_start_pos)
            self.left_animation.setEndValue(left_end_pos)

            self.right_animation.setStartValue(right_start_pos)
            self.right_animation.setEndValue(right_end_pos)

            # 启动动画
            self.left_animation.start()
            self.right_animation.start()


    def setButtonVisible(self):
        if self.CenterButton.isChecked():
            self.LeftButton.show()
            self.RightButton.show()
        else:
            self.LeftButton.hide()
            self.RightButton.hide()

    def setLeftText(self, text):
        self.CenterButton.setLeftNumber(np.round(text,2))

    def setRightText(self, text):
        self.CenterButton.setRightNumber(np.round(text,2))

    def setCenterText(self, text):
        self.CenterButton.setCenterNumber(np.round(text,2))

    def setCenterNumber(self, number):
        self.CenterButton.setCenterText(number)

    def setPositionByWidget(self, widget, TopOrBottom):
        # 获取所给窗口的位置和大小
        widget_geometry = widget.geometry
        widget_width = widget_geometry.width()
        widget_height = widget_geometry.height()

        # 获取本窗口的大小
        self_width = self.width
        self_height = self.height

        # 计算本窗口的位置
        if TopOrBottom == 'top':
            x = (widget_width - self_width) // 2
            y = 5
        elif TopOrBottom == 'bottom':
            x = (widget_width - self_width) // 2
            y = widget_height - 5- self_height

        print(x, y)
        # 设置本窗口的位置
        self.move(x, y)
                # 记录左右侧按钮的位置


class DistanceCaculate():
    def __init__(self):
        self.polydata=None

    
    def initLocator(self,filename):
        if filename=='Femur':
            path='static/asset/ssm/'+filename+'1.stl'
        else:
            path='static/asset/ssm/'+filename+'11.stl'
        reader = vtk.vtkSTLReader()
        reader.SetFileName(path)
        reader.Update()
        self.polydata = reader.GetOutput()
        self.locator = vtk.vtkImplicitPolyDataDistance()
        self.locator.SetInput(self.polydata)


    def getDistance(self,point):
        point[0]=-point[0]
        point[1]=-point[1]
        closestPointOnSurface_World = np.zeros(3)
        d=self.locator.EvaluateFunctionAndGetClosestPoint(point,closestPointOnSurface_World)
        return -d
    


        
        

FemurModelCAculater=None
TibiaModelCAculater=None


class TransformMatrix:
    def __init__(self, name, matrix):
        self.matrix = matrix
        self.parent = None
        self.name = name

    def getName(self):
        return self.name

    def setParent(self, parent):
        self.parent = parent

    def setMatrix(self, matrix):
        self.matrix = matrix

    def getAllParents(self):
        parents = []
        current = self.parent
        while current:
            parents.append(current.matrix)
            current = current.parent
        return parents

    def getFullMatrix(self):
        parents = self.getAllParents()
        result = self.matrix
        for rotation in parents:
            result = np.dot(rotation, result)
        return result


class Markup:
    def __init__(self, name):
        self.name = name
        self.points = []
        self.parent = None

    def setName(self, name):
        self.name = name

    def getName(self):
        return self.name

    def getPoints(self):
        return self.points

    def getPointsWorld(self):
        if self.parent == None:
            return self.points
        else:
            trans = self.parent.getFullMatrix()
            transformedPoints = []
            for point in self.points:
                transformedPoint = np.dot(trans, [point[0], point[1], point[2], 1])
                transformedPoints.append(transformedPoint[0:3])
            return transformedPoints

    def AddPoints(self, point):
        self.points.append(point)

    def RemoveAllPoints(self):
        self.points = []

    def RemovePointByIndex(self, index):
        self.points.pop(index)


class MyVTKScene:
    def __init__(self):
        self.Markups = []
        self.TransForms = []

    def AddMarkups(self, name):
        Markups = Markup(name)
        self.Markups.append(Markups)
        return Markups

    def RemoveMarkups(self, name):
        self.Markups = [model for model in self.Markups if model.getName() != name]

    def getMarkupsByName(self, name):
        return next((model for model in self.Markups if model.getName() == name), None)

    def AddTransform(self, name, trans):
        Trans = TransformMatrix(name, trans)
        self.TransForms.append(Trans)
        return Trans

    def RemoveTransform(self, name):
        self.TransForms = [model for model in self.TransForms if model.getName() != name]

    def getTransformByName(self, name):
        return next((model for model in self.TransForms if model.getName() == name), None)




class ssm:
    def __init__(self):
        self.Femur_list = None
        self.judge = None
        self.femurOrTibia = None
        self.FilePath = "static/asset/ssm"
        self.myScene = MyVTKScene()
    
    def preparPoints_femur(self):
        Points = self.Femur_list[0:9].copy()
        self.FemurPoints = ['开髓点', '内侧凹点', '外侧凸点', '内侧远端', '外侧远端', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点']
        self.TibiaPoints = ['胫骨隆凸', '胫骨结节', '外侧高点', '内侧高点']
        femur_index = [0, 6, 5, 4, 3, 2, 1, 7, 8]
        self.keypoints = Points[femur_index]
        for i in range(len(self.FemurPoints)):
            point = self.myScene.AddMarkups(self.FemurPoints[i])
            point.AddPoints(self.Femur_list[i].copy())
        point = self.myScene.AddMarkups('股骨头球心')
        point.AddPoints(self.Femur_list[10])
        point = self.myScene.AddMarkups('H点')
        point.AddPoints(self.Femur_list[9])
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        # if self.judge == 'L':
        #     self.keypoints[:, 0] = -self.keypoints[:, 0]
        #     self.Femur_list[:, 0] = -self.Femur_list[:, 0]

    def preparPoints_tibia(self):
        Points = self.Femur_list[0:11]
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        self.TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘']

        self.keypoints = Points[0:9].copy()
        for i in range(len(self.keypoints)):
            point = self.myScene.AddMarkups(self.TibiaPoints[i])
            point.AddPoints(self.keypoints[i].copy())
        point1 = self.myScene.AddMarkups('踝穴中心')
        point1.AddPoints((Points[9]+Points[10])/2)
        # if self.judge == 'L':
        #     self.keypoints[:, 0] = -self.keypoints[:, 0]
        #     self.Femur_list[:, 0] = -self.Femur_list[:, 0]

    # 计算在应用过转换后的点列到一个模型表面的平均距离
    def ComputeMeanDistance(self, inputFiducials, inputModel, transform):
        surfacePoints = vtk.vtkPoints()
        cellId = vtk.mutable(0)
        subId = vtk.mutable(0)
        dist2 = vtk.mutable(0.0)
        locator = vtk.vtkCellLocator()
        locator.SetDataSet(inputModel)
        locator.SetNumberOfCellsPerBucket(1)
        locator.BuildLocator()
        totalDistance = 0.0
        n = inputFiducials.shape[0]
        m = vtk.vtkMath()
        for fiducialIndex in range(0, n):
            originalPoint = [inputFiducials[fiducialIndex, 0], inputFiducials[fiducialIndex, 1],
                             inputFiducials[fiducialIndex, 2], 1]
            transformedPoint = np.dot(transform, originalPoint)
            surfacePoint = [0, 0, 0]
            transformedPoint = transformedPoint[:3]
            locator.FindClosestPoint(transformedPoint, surfacePoint, cellId, subId, dist2)
            totalDistance = totalDistance + math.sqrt(dist2)
        return (totalDistance / n)

    # 使点列到一个模型表面距离最小
    def loss_function_Femur(self, alpha):
        B = self.eigenvectors.T
        index = [7841, 6968, 3089, 8589, 2161, 7462, 2410, 7457, 7692]
        # Generate new points using weights and principal components
        new_points = self.mean_shape + np.dot(B, alpha).reshape((10000, 3))
        points = self.polydata_target.GetPoints()
        for i in range(len(new_points)):
            points.SetPoint(i, new_points[i])
        self.polydata_target.Modified()
        for i in range(9):
            self.fix_point.SetPoint(i, new_points[index[i]][0], new_points[index[i]][1], new_points[index[i]][2])
        self.fix_point.Modified()
        self.landmarkTransform.Update()
        # convert the transform matrix to a numpy array
        trans = np.zeros((4, 4))
        for i in range(4):
            for j in range(4):
                trans[i][j] = self.landmarkTransform.GetMatrix().GetElement(i, j)
        d = self.ComputeMeanDistance(self.meshPoints, self.polydata_target, trans)
        print(d)
        return d

    # 使点列到一个模型表面距离最小
    def loss_function_Tibia(self, alpha):
        B = self.eigenvectors.T
        index = [6304, 178, 4235, 1883, 7370, 6161, 4677, 6264, 1927]
        # Generate new points using weights and principal components
        new_points = self.mean_shape + np.dot(B, alpha).reshape((10000, 3))
        points = self.polydata_target.GetPoints()
        for i in range(len(new_points)):
            points.SetPoint(i, new_points[i])
        self.polydata_target.Modified()
        for i in range(9):
            self.fix_point.SetPoint(i, new_points[index[i]][0], new_points[index[i]][1], new_points[index[i]][2])
        self.fix_point.Modified()
        self.landmarkTransform.Update()
        trans = np.zeros((4, 4))
        for i in range(4):
            for j in range(4):
                trans[i][j] = self.landmarkTransform.GetMatrix().GetElement(i, j)
        d = self.ComputeMeanDistance(self.meshPoints, self.polydata_target, trans)
        

        return d


    #配准过程中调用的函数
    def distance(self, p1, p2):
       p3 = p1 - p2
       d = np.sqrt(np.dot(p3, p3))
       return d

    def move(self, data, i, target):
        n = target - data[i]
        r = 30
        point_index = []
        point_d = []
        for j in range(len(data)):
          d = self.distance(data[j], data[i])
          if d < r:
            point_index.append(j)
            point_d.append(d)
        for j in range(len(point_index)):
          data[point_index[j]] = (1 - point_d[j] / r) * n + data[point_index[j]]
        return data

    def panduan(self, old_target, target):
        hh = {}
        for i in range(len(old_target)):
          d = self.distance(old_target[i], target)
          # print(d)
          hh[i] = d
        return int(min(hh, key=hh.get))


    def moveSurfaceToTarget(self, data, target):
        for i in range(len(target)):
            idx = self.panduan(data, target[i])
            # print(idx)
            data = self.move(data, idx, target[i])
        return data


    def FemurNihe(self, meshPoints):
        self.meshPoints = meshPoints
        for i in range(len(self.keypoints)):
            self.keypoints[i][0] = -self.keypoints[i][0]
            self.keypoints[i][1] = -self.keypoints[i][1]

        for i in range(len(self.meshPoints)):
            self.meshPoints[i][0] = -self.meshPoints[i][0]
            self.meshPoints[i][1] = -self.meshPoints[i][1]
        self.mean_shape = np.load(self.FilePath + '/mean_femur.npy')
        self.eigenvectors = np.load(self.FilePath + '/ssm_femur.npy')
        targetReader = vtk.vtkPolyDataReader()
        targetReader.SetFileName(self.FilePath + '/Femur.vtk')
        targetReader.Update()
        self.polydata_target = targetReader.GetOutput()
        # 配准相关
        self.fix_point = vtk.vtkPoints()
        self.fix_point.SetNumberOfPoints(9)
        mov_point = vtk.vtkPoints()
        mov_point.SetNumberOfPoints(9)
        for i in range(9):
            mov_point.SetPoint(i, self.keypoints[i][0], self.keypoints[i][1], self.keypoints[i][2])
        self.landmarkTransform = vtk.vtkLandmarkTransform()
        self.landmarkTransform.SetModeToRigidBody()
        self.landmarkTransform.SetSourceLandmarks(mov_point)
        self.landmarkTransform.SetTargetLandmarks(self.fix_point)
        # Initial weights
        x0 = np.zeros(30)

        # Minimize loss function using Levenberg–Marquardt algorithm
        res = minimize(self.loss_function_Femur, x0, method='COBYLA')

        # Get optimized weights
        optimized_weights = res.x


        # Generate new points using optimized weights and principal components
        B = self.eigenvectors.T
        new_points = self.mean_shape + np.dot(B, optimized_weights).reshape((10000, 3))
        trans = np.zeros((4, 4))
        for i in range(4):
            for j in range(4):
                trans[i][j] = self.landmarkTransform.GetMatrix().GetElement(i, j)


       #应用trans至self.meshPoints
        for i in range(len(self.meshPoints)):
            self.meshPoints[i]=np.dot(trans,[self.meshPoints[i][0],self.meshPoints[i][1],self.meshPoints[i][2],1])[0:3]

        new_shape_3 = new_points
        #拟合后使点位于面上
        new_shape_3=self.moveSurfaceToTarget(new_shape_3, self.meshPoints)

        os.remove(self.FilePath + '/Femur.vtk')

        hhh = new_shape_3.tolist()
        mesh = open(self.FilePath + '/mesh_femur.txt').readlines()
        for i in range(len(mesh)):
            hhh.append(mesh[i].replace('\n', ''))

        f = open(self.FilePath + '/out.txt', 'a+')
        f.write('''# vtk DataFile Version 3.0
                vtk output
                ASCII
                DATASET POLYDATA
                POINTS 10000 float''')

        for i in range(len(hhh)):
            f.write(f"\n{str(hhh[i]).replace(',', ' ').replace('[', '').replace(']', '')}")
        f.close()

        os.rename(self.FilePath + '/out.txt', self.FilePath + '/Femur.vtk')
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])

        self.trans_femur = np.linalg.inv(trans)
        #self.trans_femur = np.dot(Ftrans1, np.dot(trans_ni, Ftrans1))
        # if self.judge == 'L':
        #     FemurTrans = np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        #     # self.HardModel(self.FilePath + '/Femur.stl', FemurTrans)
        #     # self.trans_femur = np.dot(FemurTrans, self.trans_femur)
        #     self.trans_femur = np.dot(FemurTrans, self.trans_femur)
        #self.trans_femur = np.dot(Ftrans1, np.dot(self.trans_femur, Ftrans1))
        #self.SmmothModel(self.FilePath + '/Femur.vtk')
        self.HardModel(self.FilePath + '/Femur.vtk',self.trans_femur)
        #model=slicer.util.loadModel(self.FilePath + '/Femur.stl')

    def TibiaNihe(self, meshPoints):
        self.meshPoints = meshPoints
        for i in range(len(self.keypoints)):
            self.keypoints[i][0] = -self.keypoints[i][0]
            self.keypoints[i][1] = -self.keypoints[i][1]

        for i in range(len(self.meshPoints)):
            self.meshPoints[i][0] = -self.meshPoints[i][0]
            self.meshPoints[i][1] = -self.meshPoints[i][1]
        self.mean_shape = np.load(self.FilePath + '/mean_tibia.npy')
        self.eigenvectors = np.load(self.FilePath + '/ssm_tibia.npy')
        print('self.keypoints',self.keypoints)
        targetReader = vtk.vtkPolyDataReader()  
        targetReader.SetFileName(self.FilePath + '/Tibia.vtk')
        targetReader.Update()
        self.polydata_target = targetReader.GetOutput()
        # 配准相关
        self.fix_point = vtk.vtkPoints()
        self.fix_point.SetNumberOfPoints(9)
        mov_point = vtk.vtkPoints()
        mov_point.SetNumberOfPoints(9)
        for i in range(9):
            mov_point.SetPoint(i, self.keypoints[i][0], self.keypoints[i][1], self.keypoints[i][2])
        self.landmarkTransform = vtk.vtkLandmarkTransform()
        self.landmarkTransform.SetModeToRigidBody()
        self.landmarkTransform.SetSourceLandmarks(mov_point)
        self.landmarkTransform.SetTargetLandmarks(self.fix_point)
        # Initial weights
        x0 = np.zeros(51)

        # Minimize loss function using Levenberg–Marquardt algorithm
        res = minimize(self.loss_function_Tibia, x0, method='COBYLA')

        # Get optimized weights
        optimized_weights = res.x

        # Generate new points using optimized weights and principal components
        B = self.eigenvectors.T
        new_points = self.mean_shape + np.dot(B, optimized_weights).reshape((10000, 3))
        trans = np.zeros((4, 4))
        for i in range(4):
            for j in range(4):
                trans[i][j] = self.landmarkTransform.GetMatrix().GetElement(i, j)

       #应用trans至self.meshPoints
        for i in range(len(self.meshPoints)):
            self.meshPoints[i]=np.dot(trans,[self.meshPoints[i][0],self.meshPoints[i][1],self.meshPoints[i][2],1])[0:3]
        new_shape_3 = new_points
        #拟合后使点位于面上
        # new_shape_3=self.moveSurfaceToTarget(new_shape_3, self.meshPoints)

        os.remove(self.FilePath + '/Tibia.vtk')

        hhh = new_shape_3.tolist()
        mesh = open(self.FilePath + '/mesh_tibia.txt').readlines()
        for i in range(len(mesh)):
            hhh.append(mesh[i].replace('\n', ''))

        f = open(self.FilePath + '/out.txt', 'a+')
        f.write('''# vtk DataFile Version 3.0
                vtk output
                ASCII
                DATASET POLYDATA
                POINTS 10000 float''')

        for i in range(len(hhh)):
            f.write(f"\n{str(hhh[i]).replace(',', ' ').replace('[', '').replace(']', '')}")
        f.close()

        os.rename(self.FilePath + '/out.txt', self.FilePath + '/Tibia.vtk')
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])

        self.trans_tibia = np.linalg.inv(trans)

        # if self.judge == 'L':
        #     FemurTrans = np.array([[-1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]])
        #     # self.HardModel(self.FilePath + '/Femur.stl', FemurTrans)
        #     # self.trans_femur = np.dot(FemurTrans, self.trans_femur)
        #     self.trans_tibia = np.dot(FemurTrans, self.trans_tibia)
        #self.trans_femur = np.dot(Ftrans1, np.dot(self.trans_femur, Ftrans1))
        #self.SmmothModel(self.FilePath + '/Tibia.vtk')
        self.HardModel(self.FilePath + '/Tibia.vtk',self.trans_tibia)
        #model=slicer.util.loadModel(self.FilePath + '/Tibia.stl')


    def SmmothModel(self, path1):

        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(path1)
        reader.Update()

        smoothFilter = vtk.vtkSmoothPolyDataFilter()
        smoothFilter.SetInputData(reader.GetOutput())



        # 设置平滑迭代次数为20次
        smoothFilter.SetNumberOfIterations(20)

        # 设置平滑因子（SmoothFactor）为0.1
        smoothFilter.SetRelaxationFactor(0.08)
        smoothFilter.Update()


        # 保存为vtk文件
        writer = vtk.vtkPolyDataWriter()
        writer.SetFileName(path1)
        writer.SetInputData(smoothFilter.GetOutput())
        writer.Write()

    def HardModel(self, path1, trans):

        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(path1)
        reader.Update()
        model = reader.GetOutput()
        # Define the transformation
        transformation = trans
        # Apply the transformation to the model
        transform_filter = vtk.vtkTransformFilter()
        transform = vtk.vtkTransform()
        transform.SetMatrix(transformation.flatten())
        transform_filter.SetTransform(transform)
        transform_filter.SetInputData(model)
        transform_filter.Update()
        # 保存为vtk文件
        writer = vtk.vtkPolyDataWriter()
        writer.SetFileName(path1)
        writer.SetInputData(transform_filter.GetOutput())
        writer.Write()
        



class ssmFemur:
    def __init__(self):
        self.Femur_list = None
        self.judge = None
        self.femurOrTibia = None
        self.polydata=None
        self.pointsOut = None
        self.pointsInner = None
        self.FilePath = "static/asset/ssm"
        self.outPutPath = "static/output/ssm"
        self.myScene = MyVTKScene()



    def initLocator(self,filename):
        #如果是stl文件
        if filename.endswith('.stl'):                
            reader = vtk.vtkSTLReader()
            reader.SetFileName(filename)
            reader.Update()
        elif filename.endswith('.vtk'):
            reader = vtk.vtkPolyDataReader()
            reader.SetFileName(filename)
            reader.Update()
        elif filename.endswith('.ply'):
            reader = vtk.vtkPLYReader()
            reader.SetFileName(filename)
            reader.Update()

        self.polydata = reader.GetOutput()
        self.locator = vtk.vtkImplicitPolyDataDistance()
        self.locator.SetInput(self.polydata)
    def updateLocator(self):
        self.locator.SetInput(self.polydata)



    def getDistance(self,point):
        point[0]=-point[0]
        point[1]=-point[1]
        closestPointOnSurface_World = np.zeros(3)
        d=self.locator.EvaluateFunctionAndGetClosestPoint(point,closestPointOnSurface_World)
        return -d
    
    def getClosestPoint(self,point):
        point[0]=-point[0]
        point[1]=-point[1]
        closestPointOnSurface_World = np.zeros(3)
        d=self.locator.EvaluateFunctionAndGetClosestPoint(point,closestPointOnSurface_World)
        closestPointOnSurface_World[0]=-closestPointOnSurface_World[0]
        closestPointOnSurface_World[1]=-closestPointOnSurface_World[1]
        return closestPointOnSurface_World



    def remeshModel(self,path):
        # 读取输入的模型文件
        reader = vtk.vtkSTLReader()
        reader.SetFileName(path)
        reader.Update()
        smoothFilter = vtk.vtkSmoothPolyDataFilter()
        smoothFilter.SetInputData(reader.GetOutput())



        # 设置平滑迭代次数为20次
        smoothFilter.SetNumberOfIterations(20)

        # 设置平滑因子（SmoothFactor）为0.1
        smoothFilter.SetRelaxationFactor(0.08)
        smoothFilter.Update()
        # tri_filter = vtk.vtkTriangleFilter()
        # tri_filter.SetInputData(smoothFilter.GetOutput())
        # tri_filter.Update()
        # inputMesh = pv.wrap(tri_filter.GetOutput())
        # clus = pyacvd.Clustering(inputMesh)

        # clus.subdivide(2)
        # clus.cluster(5000)
        # outputMesh = vtk.vtkPolyData()
        # outputMesh.DeepCopy(clus.create_mesh())
        # 保存重构后的表面模型
        writer = vtk.vtkSTLWriter()
        writer.SetFileName(path)
        writer.SetInputData(smoothFilter.GetOutput())
        writer.Write()



    def scaleModel(self,inputPath,scaleX=1.0, scaleY=1.0, scaleZ=1.0):
        """Mesh relaxation based on vtkWindowedSincPolyDataFilter.
        Scale of 1.0 means original size, >1.0 means magnification.
        """
        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(inputPath)
        reader.Update()
        model = reader.GetOutput()
        transform = vtk.vtkTransform()
        transform.Scale(scaleX, scaleY, scaleZ)
        transformFilter = vtk.vtkTransformFilter()
        transformFilter.SetInputData(model)
        transformFilter.SetTransform(transform)

        if transform.GetMatrix().Determinant() >= 0.0:
            transformFilter.Update()
            writer = vtk.vtkSTLWriter()
            writer.SetFileName(inputPath.replace('.vtk', '.stl'))
            writer.SetInputData(transformFilter.GetOutput())
            writer.Write()

    def registion(self,points_From, points_To):
        if len(points_From)!=len(points_To):
            return
        fix_point = vtk.vtkPoints()
        fix_point.SetNumberOfPoints(len(points_From))
        mov_point = vtk.vtkPoints()
        mov_point.SetNumberOfPoints(len(points_From))
        for i in range(len(points_From)):
            mov_point.SetPoint(i, points_From[i][0], points_From[i][1], points_From[i][2])
            fix_point.SetPoint(i, points_To[i][0], points_To[i][1], points_To[i][2])
            
        fix_point.Modified()
        mov_point.Modified()
        landmarkTransform = vtk.vtkLandmarkTransform()
        landmarkTransform.SetModeToRigidBody()
        landmarkTransform.SetSourceLandmarks(mov_point)
        landmarkTransform.SetTargetLandmarks(fix_point)

        landmarkTransform.Update()
        trans = np.zeros((4, 4))
        for i in range(4):
            for j in range(4):
                trans[i][j] = landmarkTransform.GetMatrix().GetElement(i, j)
        return trans

    def startGuihua(self):
        pass

    def preparPointsForFemurGuihua(self,points,femurUp):
        points=np.array(points)
        self.FemurPoints = ['开髓点', '内侧凹点', '外侧凸点', '内侧远端', '外侧远端', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点','股骨头球心', 'H点']
        for i in range(len(self.FemurPoints)):
            point = self.myScene.AddMarkups(self.FemurPoints[i])
            point.AddPoints(points[i].copy())
        point = self.myScene.AddMarkups('femurUp1')
        point.AddPoints(femurUp[0])
        point = self.myScene.AddMarkups('femurUp2')
        point.AddPoints(femurUp[1])


    def prparModel(self,path):
        self.initLocator(path)



    def preparPoints_tibia(self):
        Points = self.Femur_list[0:11]
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        self.TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘']

        self.keypoints = Points[0:9].copy()
        for i in range(len(self.keypoints)):
            point = self.myScene.AddMarkups(self.TibiaPoints[i])
            point.AddPoints(self.keypoints[i].copy())
        point1 = self.myScene.AddMarkups('踝穴中心')
        point1.AddPoints((Points[9]+Points[10])/2)
        if self.judge == 'L':
            self.keypoints[:, 0] = -self.keypoints[:, 0]
            self.Femur_list[:, 0] = -self.Femur_list[:, 0]

    def HardModel(self, trans):
        # Apply the transformation to the model
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        transformation = np.dot(np.dot(Ftrans1, trans), Ftrans1)
        transform_filter = vtk.vtkTransformPolyDataFilter()
        transform = vtk.vtkTransform()
        transform.SetMatrix(transformation.flatten())
        transform_filter.SetTransform(transform)
        transform_filter.SetInputData(self.polydata)
        transform_filter.Update()
        self.polydata = transform_filter.GetOutput()
    def HardModel1(self, path1, trans):
        if "vtk" in path1:
            reader = vtk.vtkPolyDataReader()
            reader.SetFileName(path1)
            path1=path1.replace("vtk", "stl")
        else:
            reader = vtk.vtkSTLReader()
            reader.SetFileName(path1)

        reader.Update()
        model = reader.GetOutput()
        # Define the transformation
        transformation = trans
        # Apply the transformation to the model
        transform_filter = vtk.vtkTransformFilter()
        transform = vtk.vtkTransform()
        transform.SetMatrix(transformation.flatten())
        transform_filter.SetTransform(transform)
        transform_filter.SetInputData(model)
        transform_filter.Update()



        writer = vtk.vtkSTLWriter()
        writer.SetFileName(path1)
        writer.SetInputData(transform_filter.GetOutput())
        writer.Write()


    def onGuGuTouConfirm(self,points):
        points = points.astype(np.float64)  # 防止溢出
        num_points = points.shape[0]
        print(num_points)
        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2]
        x_avr = sum(x) / num_points
        y_avr = sum(y) / num_points
        z_avr = sum(z) / num_points
        xx_avr = sum(x * x) / num_points
        yy_avr = sum(y * y) / num_points
        zz_avr = sum(z * z) / num_points
        xy_avr = sum(x * y) / num_points
        xz_avr = sum(x * z) / num_points
        yz_avr = sum(y * z) / num_points
        xxx_avr = sum(x * x * x) / num_points
        xxy_avr = sum(x * x * y) / num_points
        xxz_avr = sum(x * x * z) / num_points
        xyy_avr = sum(x * y * y) / num_points
        xzz_avr = sum(x * z * z) / num_points
        yyy_avr = sum(y * y * y) / num_points
        yyz_avr = sum(y * y * z) / num_points
        yzz_avr = sum(y * z * z) / num_points
        zzz_avr = sum(z * z * z) / num_points

        A = np.array([[xx_avr - x_avr * x_avr, xy_avr - x_avr * y_avr, xz_avr - x_avr * z_avr],
                    [xy_avr - x_avr * y_avr, yy_avr - y_avr * y_avr, yz_avr - y_avr * z_avr],
                    [xz_avr - x_avr * z_avr, yz_avr - y_avr * z_avr, zz_avr - z_avr * z_avr]])
        b = np.array([xxx_avr - x_avr * xx_avr + xyy_avr - x_avr * yy_avr + xzz_avr - x_avr * zz_avr,
                    xxy_avr - y_avr * xx_avr + yyy_avr - y_avr * yy_avr + yzz_avr - y_avr * zz_avr,
                    xxz_avr - z_avr * xx_avr + yyz_avr - z_avr * yy_avr + zzz_avr - z_avr * zz_avr])
        # print(A, b)
        b = b / 2
        center = np.linalg.solve(A, b)
        x0 = center[0]
        y0 = center[1]
        z0 = center[2]
        r2 = xx_avr - 2 * x0 * x_avr + x0 * x0 + yy_avr - 2 * y0 * y_avr + y0 * y0 + zz_avr - 2 * z0 * z_avr + z0 * z0
        r = r2 ** 0.5
        print(center, r)
        return center


    # 建立股骨坐标系，股骨头球心，开髓点，外侧凸点，内侧凹点
    def creatCordingnate_femur(self):
        ras1 = self.myScene.getMarkupsByName('股骨头球心').getPoints()[0]
        ras2 = self.myScene.getMarkupsByName('开髓点').getPoints()[0]
        ras3 = self.myScene.getMarkupsByName('外侧凸点').getPoints()[0]
        ras4 = self.myScene.getMarkupsByName('内侧凹点').getPoints()[0]
        zb1 = [ras1[0], ras1[1], ras1[2]]  # 坐标1，球心
        zb2 = [ras2[0], ras2[1], ras2[2]]  # 坐标2，原点
        zb3 = [ras3[0], ras3[1], ras3[2]]  # 坐标3，左侧点
        zb4 = [ras4[0], ras4[1], ras4[2]]  # 坐标4，右侧点
        jxlz = [0, 0, 0]  # Y轴基向量
        for i in range(0, 3):
            jxlz[i] = zb1[i]-zb2[i]
        moz = np.sqrt(np.square(jxlz[0]) + np.square(jxlz[1]) + np.square(jxlz[2]))  # 基向量z的模
        for i in range(0, 3):
            jxlz[i] = jxlz[i] / moz
        csD = jxlz[0] * zb2[0] + jxlz[1] * zb2[1] + jxlz[2] * zb2[2]  # 平面方程参数D
        csT3 = (jxlz[0] * zb3[0] + jxlz[1] * zb3[1] + jxlz[2] * zb3[2] - csD) / (
                jxlz[0] * jxlz[0] + jxlz[1] * jxlz[1] + jxlz[2] * jxlz[2])  # 坐标3平面方程参数T
        ty3 = [0, 0, 0]  # 坐标3在YZ平面的投影
        for i in range(0, 3):
            ty3[i] = zb3[i] - jxlz[i] * csT3
        csT4 = (jxlz[0] * zb4[0] + jxlz[1] * zb4[1] + jxlz[2] * zb4[2] - csD) / (
                jxlz[0] * jxlz[0] + jxlz[1] * jxlz[1] + jxlz[2] * jxlz[2])
        ty4 = [0, 0, 0]
        for i in range(0, 3):
            ty4[i] = zb4[i] - jxlz[i] * csT4
        jxlx = [0, 0, 0]  # X轴基向量
        for i in range(0, 3):  #########判断左右腿
            # if self.judge == 'L':
            #     jxlx[i] = ty3[i] - ty4[i]
            # else:
            jxlx[i] = ty4[i] - ty3[i]
        mox = np.sqrt(np.square(jxlx[0]) + np.square(jxlx[1]) + np.square(jxlx[2]))  # 基向量X的模
        for i in range(0, 3):
            jxlx[i] = jxlx[i] / mox
        jxly = [0, 0, 0]  # y轴基向量
        jxly[0] = (jxlx[1] * jxlz[2] - jxlx[2] * jxlz[1])
        jxly[1] = (jxlx[2] * jxlz[0] - jxlx[0] * jxlz[2])
        jxly[2] = (jxlx[0] * jxlz[1] - jxlx[1] * jxlz[0])
        moy = np.sqrt(np.square(jxly[0]) + np.square(jxly[1]) + np.square(jxly[2]))  # 基向量y的模
        for i in range(0, 3):
            jxly[i] = jxly[i] / moy

        cord = np.zeros((4, 4))
        cord[0:3, 0] = jxlx
        cord[0:3, 1] = jxly
        cord[0:3, 2] = jxlz
        cord[0:3, 3] = zb2
        cord[3, 3] = 1
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        Ftrans3 = np.dot(Ftrans1,np.linalg.inv(cord))
        FemurHardTrans = Ftrans3
        # Ftrans1 = np.array([[-1, 0, 0, 0],
        #                     [0, -1, 0, 0],
        #                     [0, 0, 1, 0],
        #                     [0, 0, 0, 1]])
        # FemurHardTrans = np.dot(np.dot(Ftrans1, FemurHardTrans), Ftrans1)
        # word = np.dot(np.dot(Ftrans1, FemurHardTrans), Ftrans1)
        self.HardModel(FemurHardTrans)
        self.updateLocator()
        writer = vtk.vtkSTLWriter()
        writer.SetFileName("d:/data/Femur.stl")
        writer.SetInputData(self.polydata)
        writer.Write()
        points=[]
        FemurPoints = ['开髓点', '内侧凹点', '外侧凸点', '内侧远端', '外侧远端', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点', "股骨头球心", 'H点', "femurUp1", "femurUp2"]
        for i in range(len(FemurPoints)):
            PointNode = self.myScene.AddMarkups(FemurPoints[i] + "1")
            point = self.myScene.getMarkupsByName(FemurPoints[i]).getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.AddPoints(np.dot(Ftrans3, point)[0:3])
            points.append(list(np.dot(Ftrans3, point)[0:3]))
        #self.updateLowPoints(Ftrans3)

        print("pointspointspointspointspointspoints:",points)


    def updateLowPoints(self,trans,index=0):
        for i in range(len(self.pointsOut)):
            self.pointsOut[i]=(np.dot(trans, [self.pointsOut[i][0], self.pointsOut[i][1], self.pointsOut[i][2], 1])[0:3])

        for i in range(len(self.pointsInner)):
            self.pointsInner[i]=(np.dot(trans,[self.pointsInner[i][0],self.pointsInner[i][1],self.pointsInner[i][2],1])[0:3])
        self.pointsInner=list(self.pointsInner)
        self.pointsOut=list(self.pointsOut)
        #获取pointsInnerZ轴最低点
        if index==0:
            self.pointsInner.sort(key=lambda x:x[2])
            self.pointsOut.sort(key=lambda x:x[2])
        else:
            self.pointsInner.sort(key=lambda x:x[1])
            self.pointsOut.sort(key=lambda x:x[1])
            #倒序
            self.pointsInner.reverse()
            self.pointsOut.reverse()
        point = self.myScene.getMarkupsByName('内侧远端1')
        point.RemoveAllPoints()
        point.AddPoints(self.pointsInner[0])
        point = self.myScene.getMarkupsByName('外侧远端1')
        point.RemoveAllPoints()
        point.AddPoints(self.pointsOut[0])

        #获取pointsInnerY轴最低点
        if index==0:
            self.pointsInner.sort(key=lambda x:x[1])
            self.pointsOut.sort(key=lambda x:x[1])
        else:
            self.pointsInner.sort(key=lambda x:x[2])
            self.pointsOut.sort(key=lambda x:x[2])
        point = self.myScene.getMarkupsByName('内侧后髁1')

        point.RemoveAllPoints()
        point.AddPoints(self.pointsInner[0])
        point = self.myScene.getMarkupsByName('外侧后髁1')
        print(self.pointsOut[0])
        print(point.getPoints()[0])
        point.RemoveAllPoints()
        point.AddPoints(self.pointsOut[0])






    def creatCordingnate_tibia(self):

        ras1 = self.myScene.getMarkupsByName('胫骨隆凸').getPoints()[0]
        ras2 = self.myScene.getMarkupsByName('胫骨结节').getPoints()[0]
        ras3 = self.myScene.getMarkupsByName('踝穴中心').getPoints()[0]


        Tzb1 = [ras1[0], ras1[1], ras1[2]]  # 坐标1，原点，髌骨近端的点
        Tzb2 = [ras2[0], ras2[1], ras2[2]]  # 坐标2，髌骨中间的点
        Tzb3 = [ras3[0], ras3[1], ras3[2]]  # 坐标2，髌骨远端的点
        Tjxlz = [0, 0, 0]  # z轴基向量
        for i in range(0, 3):
            Tjxlz[i] = Tzb1[i] - Tzb3[i]
        moz = np.sqrt(np.square(Tjxlz[0]) + np.square(Tjxlz[1]) + np.square(Tjxlz[2]))  # 基向量z的模
        for i in range(0, 3):
            Tjxlz[i] = Tjxlz[i] / moz
        TcsD = Tjxlz[0] * Tzb1[0] + Tjxlz[1] * Tzb1[1] + Tjxlz[2] * Tzb1[2]  # 平面方程参数D
        TcsT2 = (Tjxlz[0] * Tzb2[0] + Tjxlz[1] * Tzb2[1] + Tjxlz[2] * Tzb2[2] - TcsD) / (
                Tjxlz[0] * Tjxlz[0] + Tjxlz[1] * Tjxlz[1] + Tjxlz[2] * Tjxlz[2])  # 坐标3平面方程参数T
        Tty2 = [0, 0, 0]  # 坐标2在XY平面的投影
        for i in range(0, 3):
            Tty2[i] = Tzb2[i] - Tjxlz[i] * TcsT2
        Tjxly = [0, 0, 0]  # y轴基向量
        for i in range(0, 3):
            Tjxly[i] = Tzb1[i] - Tty2[i]
        moy = np.sqrt(np.square(Tjxly[0]) + np.square(Tjxly[1]) + np.square(Tjxly[2]))  # 基向量y的模
        for i in range(0, 3):
            Tjxly[i] = Tjxly[i] / moy
        Tjxlx = [0, 0, 0]  # x轴基向量
        Tjxlx[0] = (Tjxlz[1] * Tjxly[2] - Tjxlz[2] * Tjxly[1])
        Tjxlx[1] = (Tjxlz[2] * Tjxly[0] - Tjxlz[0] * Tjxly[2])
        Tjxlx[2] = (Tjxlz[0] * Tjxly[1] - Tjxlz[1] * Tjxly[0])
        mox = np.sqrt(np.square(Tjxly[0]) + np.square(Tjxly[1]) + np.square(Tjxly[2]))  # 基向量x的模
        for i in range(0, 3):
            Tjxlx[i] = Tjxlx[i] / mox
        Tzb3xz = []
        jd = 1
        jd = math.radians(jd)
        zhjz = np.array([[Tjxlx[0], Tjxly[0], Tjxlz[0], Tzb1[0]], [Tjxlx[1], Tjxly[1], Tjxlz[1], Tzb1[1]],
                [Tjxlx[2], Tjxly[2], Tjxlz[2], Tzb1[2]], [0, 0, 0, 1]])
        Tzb3xz3 = self.GetMarix(zhjz,1,Tzb3)
        # for i in range(0, 3):
        #     Tzb3[i] = Tzb3xz3[i]
        Tjxlz = [0, 0, 0]  # z轴基向量
        for i in range(0, 3):
            Tjxlz[i] = Tzb1[i] - Tzb3[i]
        moz = np.sqrt(np.square(Tjxlz[0]) + np.square(Tjxlz[1]) + np.square(Tjxlz[2]))  # 基向量z的模
        for i in range(0, 3):
            Tjxlz[i] = Tjxlz[i] / moz
        TcsD = Tjxlz[0] * Tzb1[0] + Tjxlz[1] * Tzb1[1] + Tjxlz[2] * Tzb1[2]  # 平面方程参数D
        TcsT2 = (Tjxlz[0] * Tzb2[0] + Tjxlz[1] * Tzb2[1] + Tjxlz[2] * Tzb2[2] - TcsD) / (
                Tjxlz[0] * Tjxlz[0] + Tjxlz[1] * Tjxlz[1] + Tjxlz[2] * Tjxlz[2])  # 坐标3平面方程参数T
        Tty2 = [0, 0, 0]  # 坐标2在XY平面的投影
        for i in range(0, 3):
            Tty2[i] = Tzb2[i] - Tjxlz[i] * TcsT2
        Tjxly = [0, 0, 0]  # y轴基向量
        for i in range(0, 3):
            Tjxly[i] = Tty2[i]-Tzb1[i]
        moy = np.sqrt(np.square(Tjxly[0]) + np.square(Tjxly[1]) + np.square(Tjxly[2]))  # 基向量y的模
        for i in range(0, 3):
            Tjxly[i] = Tjxly[i] / moy
        Tjxlx = [0, 0, 0]  # X轴基向量
        Tjxlx[0] = (Tjxlz[1] * Tjxly[2] - Tjxlz[2] * Tjxly[1])
        Tjxlx[1] = (Tjxlz[2] * Tjxly[0] - Tjxlz[0] * Tjxly[2])
        Tjxlx[2] = (Tjxlz[0] * Tjxly[1] - Tjxlz[1] * Tjxly[0])
        mox = np.sqrt(np.square(Tjxlx[0]) + np.square(Tjxlx[1]) + np.square(Tjxlx[2]))  # 基向量x的模
        for i in range(0, 3):
            Tjxlx[i] = Tjxlx[i] / mox
        ccb = ([Tjxlx, Tjxly, Tjxlz])
        ccc = np.asarray(ccb)
        ccd = ccc.T
        #np.savetxt(self.FilePath + "/Tibia-jxl.txt", ccd, fmt='%6f')
        Ttrans1 = np.array([[1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        Ttrans2 = np.array([[float(Tjxlx[0]), float(Tjxly[0]), float(Tjxlz[0]), Tzb1[0]],
                                [float(Tjxlx[1]), float(Tjxly[1]), float(Tjxlz[1]), Tzb1[1]],
                                [float(Tjxlx[2]), float(Tjxly[2]), float(Tjxlz[2]), Tzb1[2]],
                                [0, 0, 0, 1]])
        self.Ttrans3=np.dot(Ttrans1,np.linalg.inv(Ttrans2))
        Ttrans4 = np.array([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        


        print("Ttrans2",Ttrans2)
        Ftransform1 = self.myScene.AddTransform('变换_胫骨临时', self.Ttrans3)
        Ftransform11 = self.myScene.AddTransform('变换_胫骨约束', Ttrans4)
        Ftransform12 = self.myScene.AddTransform('变换_胫骨调整', Ttrans4)
        Ftransform12.parent = Ftransform11
        print("self.Ttrans3",self.Ttrans3)


        self.TibiaHardTrans =self.Ttrans3
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        self.TibiaHardTrans=np.dot(self.TibiaHardTrans, Ftrans1)
        self.WordToReal = np.dot(Ftrans1, self.Ttrans3)
        #self.TibiaHardTrans = np.dot(Ftrans1, self.TibiaHardTrans)
        #self.TibiaHardTrans = np.dot(Ftrans1, np.dot(self.TibiaHardTrans, Ftrans1))
        #print("self.Ftrans2", self.Ftrans2)
        #print("self.Ftrans3",self.Ftrans3)
        self.HardModel(self.FilePath + '/Tibia.stl', self.TibiaHardTrans)
        #model=slicer.util.loadModel(self.FilePath + '/Tibia1.stl')


        # 将所有点复制出一份放到截骨调整中
        TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
        for i in range(len(TibiaPoints)):
            PointNode = self.myScene.AddMarkups(TibiaPoints[i] + "1")
            point = self.myScene.getMarkupsByName(TibiaPoints[i]).getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.AddPoints(np.dot(self.WordToReal, point)[0:3])
            PointNode.parent = self.myScene.getTransformByName('变换_胫骨调整')
        self.creatCordingnate_tibia_1()
      
    # 获取变换下的截骨面
    def GetTransPoint(self, name):
        if name == "股骨第一截骨面":
            p1 = self.GetTransPoint_real([15.063, 25, 0])
            p2 = self.GetTransPoint_real([0, 0, 0])
            p3 = self.GetTransPoint_real([-21.372, -23.271, 0])

        elif name == "股骨第二截骨面":
            p1 = self.GetTransPoint_real([-15.063, 23.063, 22.222])
            p2 = self.GetTransPoint_real([1.143, 23.207, 29.894])
            p3 = self.GetTransPoint_real([21.372, 23.271, 24.171])
        zb = np.array([p1, p2, p3])
        return zb

    def FirstJieGu(self):
        # 先将传过来的点，变换之原点，再变换至调整下
        point = self.myScene.getMarkupsByName('内侧远端1').getPointsWorld()[0]
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0]

        # 外侧皮质高点1'
        PointNode = self.myScene.AddMarkups('股骨第一截骨面')
        PointNode.AddPoints([30.951, -14.145, 17.976])
        PointNode.AddPoints([-31.236, -1.339, 17.976])
        PointNode.AddPoints([-31.485, -15.010, 17.976])
        PointNode.parent = self.myScene.getTransformByName("变换_股骨假体调整")

        PointNode = self.myScene.AddMarkups('股骨第二截骨面')
        PointNode.AddPoints([-16.637, 24.306-9, 21.857+18])
        PointNode.AddPoints([1.185, 25.471-9, 32.778+18])
        PointNode.AddPoints([22.742, 24.575-9, 24.382+18])
        PointNode.parent = self.myScene.getTransformByName("变换_股骨假体调整")

        Femur1JGM = self.myScene.getMarkupsByName('股骨第一截骨面').getPointsWorld()
        Femur2JGM = self.myScene.getMarkupsByName('股骨第二截骨面').getPointsWorld()
        d = self.point2area_distance(np.array(Femur1JGM), point)
        d1 = self.point2area_distance(np.array(Femur2JGM), point1)
        self.destance = d - 8
        FtransTmp = np.array([[1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, self.destance],
                    [0, 0, 0, 1]])
        self.myScene.getTransformByName("变换_股骨约束").matrix = FtransTmp
        ras1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0]
        d = self.point2area_distance(np.array(Femur2JGM), ras1)
        x = d / math.cos(math.radians(6))
        n1=[0,1,0]
        n2 = np.array(ras1) - self.TouYing(Femur2JGM, ras1)
        if np.dot(n1,n2)<0:
            direction = 1
        else:
            direction = -1
        x=direction*x
        self.record = x
        FtransTmp = np.array([[1, 0, 0, 0],
                            [0, 1, 0, x],
                            [0, 0, 1, self.destance],
                            [0, 0, 0, 1]])
        self.myScene.getTransformByName("变换_股骨约束").matrix = FtransTmp


    #将点放到正确位置
    def getDisByPlane(self,Femur2JGM,Femur3JGM):
        point0 = self.myScene.getMarkupsByName('内侧远端1').getPointsWorld()[0].copy()
        point01 = self.myScene.getMarkupsByName('外侧远端1').getPointsWorld()[0].copy()
        point=(point0+point01)/2
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0].copy()
        

        Femur1JGM = np.array([[30.951, -14.145, 17.976],
                             [-31.236, -1.339, 17.976],
                             [-31.485, -15.010, 17.976]])
        
        d = self.point2area_distance(np.array(Femur1JGM), point)
        self.destance = d - 8
        point1[2]=point1[2]+self.destance
        ras1 = point1
        d = self.point2area_distance(np.array(Femur2JGM), ras1)
        x = d / math.cos(math.radians(6))
        n1=[0,1,0]
        n2 = np.array(ras1) - self.TouYing(Femur2JGM, ras1)
        if np.dot(n1,n2)<0:
            direction = 1
        else:
            direction = -1
        x=direction*x
        points2JGMUp=(Femur2JGM[0]+Femur2JGM[1])/2
        points2JGMUp[2]=points2JGMUp[2]-self.destance
        x=(-self.getDistance(points2JGMUp)/math.cos(math.radians(6))+x)/2
        self.record = x
        FtransTmp = np.array([[1, 0, 0, 0],
                                [0, 1, 0, x],
                                [0, 0, 1, self.destance],
                                [0, 0, 0, 1]])
        
        points2JGMUp=(Femur2JGM[0]+Femur2JGM[1])/2
        points2JGMUp[2]=points2JGMUp[2]-self.destance

        # print('新的z方向距离',-self.getDistance(points2JGMUp))
        # print('jiu的x方向距离',x)


        # 旧方法，对齐后髁点
        # point2 = self.myScene.getMarkupsByName('外侧后髁1').getPointsWorld()[0].copy()
        # point3 = self.myScene.getMarkupsByName('内侧后髁1').getPointsWorld()[0].copy()
        # #对point2及point3进行变换
        # point2+=np.array([0,x,self.destance])
        # point3+=np.array([0,x,self.destance])
        # ang1Point=[point2[0],point2[1],point2[2]]
        # ang2Point=[point2[0],(point3[1]),point2[2]]
        # angle1=self.Angle(ang1Point,ang2Point)
        # print('angle1',angle1)
        # if 1:
        #     angle1+=1
        #     if point2[1]>point3[1]:
        #         angle1=-angle1
        #     #计算绕Z轴旋angle1度的矩阵
        #     martrix=self.GetMarix_z(angle1)
        #     FtransTmp=np.dot(martrix,FtransTmp)
        #     print('FtransTmp',FtransTmp)
        #     FtransTmpInv=np.linalg.inv(FtransTmp)
        #     #更新Femur2JGM及Femur3JGM
        #     for i in range(0,3):
        #         Femur2JGM[i]=np.dot(FtransTmpInv,[Femur2JGM[i][0],Femur2JGM[i][1],Femur2JGM[i][2],1])[0:3]
        #         Femur3JGM[i]=np.dot(FtransTmpInv,[Femur3JGM[i][0],Femur3JGM[i][1],Femur3JGM[i][2],1])[0:3]
        # else:
        #     Femur2JGM=Femur2JGM+np.array([0,-x,-self.destance])
        #     Femur3JGM=Femur3JGM+np.array([0,-x,-self.destance])

        #新的角度计算方法，考虑对齐皮质高点另一侧的的点及皮质高点
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0].copy()
        point1_1 = point1.copy()
        point1_1[0]=point1_1[0]-16
        #计算point1_1在骨骼上的最近点
        pointClose=self.getClosestPoint(point1_1)
        point1+=np.array([0,x,self.destance])
        pointClose+=np.array([0,x,self.destance])
        point1[0]=pointClose[0]
        angel=self.Angle(point1,pointClose)+1
        if (point1[1]>pointClose[1]):
            angel=-angel
        print('angelNew',angel)
        #计算绕Z轴旋angle1度的矩阵
        martrix=self.GetMarix_z(angel)
        FtransTmp=np.dot(martrix,FtransTmp)
        print('FtransTmp',FtransTmp)
        FtransTmpInv=np.linalg.inv(FtransTmp)
        #更新Femur2JGM及Femur3JGM
        for i in range(0,3):
            Femur2JGM[i]=np.dot(FtransTmpInv,[Femur2JGM[i][0],Femur2JGM[i][1],Femur2JGM[i][2],1])[0:3]
            Femur3JGM[i]=np.dot(FtransTmpInv,[Femur3JGM[i][0],Femur3JGM[i][1],Femur3JGM[i][2],1])[0:3]

        #前倾角度计算
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0].copy()
        point1[2]=point1[2]+35
        #计算point1在骨骼上的最近点
        pointClose=self.getClosestPoint(point1)
        #在3D slicer中添加一个markups节点，用于显示pointClose
        # PointNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        # PointNode.SetName('pointClose')
        # PointNode.AddControlPoint(pointClose)
        #计算pointClose在平面Femur2JGM上的投影点
        pointClose1=self.getProjectionPoint(pointClose,Femur2JGM)
        normal=pointClose-pointClose1
        normal=normal/np.linalg.norm(normal)
        #判断normal是否与[0,-1,0]同向
        if np.dot(normal,[0,-1,0])<0:
            angel=self.Angle(pointClose1,pointClose)
            print('angel',angel)
            martrix_x=self.GetMarix_x(angel)
            FtransTmp=np.dot(martrix_x,FtransTmp)
            martrix_x_inv=np.linalg.inv(martrix_x)
            for i in range(0,3):
                Femur2JGM[i]=np.dot(martrix_x_inv,[Femur2JGM[i][0],Femur2JGM[i][1],Femur2JGM[i][2],1])[0:3]
                Femur3JGM[i]=np.dot(martrix_x_inv,[Femur3JGM[i][0],Femur3JGM[i][1],Femur3JGM[i][2],1])[0:3]

        else:
            pass

        return Femur2JGM,Femur3JGM,FtransTmp

    #计算点在平面上的投影点，平面由三个点确定
    def getProjectionPoint(self,point,planePoints):
        planeNormal=np.cross(planePoints[1]-planePoints[0],planePoints[2]-planePoints[0])
        planeNormal=planeNormal/np.linalg.norm(planeNormal)
        return point-np.dot(planeNormal,point-planePoints[0])*planeNormal



    #计算点到平面的距离，平面由一个点及法向量确定
    def getPointToPlane(self,point,planePoint,planeNormal):
        return abs(np.dot(planeNormal,point-planePoint))
    # 推荐股骨假体
    def SelectJiaTi(self):
        #self.FirstJieGu()
        #约束条件满足后，两端到骨骼表面的距离。
        #影响条件：
        #1.后髁点到第三刀截骨面距离，与一个标准值 7mm 差越多，得分越低
        #2.覆盖率，后髁边缘离骨骼越远，分越低。前髁边缘离骨骼越远，分越低
        PointPath = self.FilePath+"/假体库/a"
        point2 = self.myScene.getMarkupsByName('外侧后髁1').getPointsWorld()[0].copy()
        point3 = self.myScene.getMarkupsByName('内侧后髁1').getPointsWorld()[0].copy()
        femurUp11=self.myScene.getMarkupsByName('femurUp11').getPointsWorld()[0].copy()
        femurUp21=self.myScene.getMarkupsByName('femurUp21').getPointsWorld()[0].copy()
        femurUpMean=(femurUp11[2]+femurUp21[2])/2

        # 假体型号
        diffList=[]
        FtransList=[]
        list3 = ['1-5', '2', '2-5', '3', '4', '5']
        planePoints=np.array([[ 21.75182915, -31.58379936,  26.24497032],
                        [ 23.03744316, -33.59889984,  30.42037392],
                        [ 23.0080719 , -34.25144196,  33.0945282 ],
                        [ 22.93015862, -34.80111694,  36.79411316],
                        [ 25.76075363, -36.34246063,  37.22349167],
                        [ 25.83369255, -38.84169388,  34.0918045 ]])
        for i in range(0, len(list3)):
            name = 'femur-' + list3[i]
            lujing = os.path.join(PointPath, name + '.txt')
            inputPoints = np.loadtxt(lujing)
            Femur2JGM=inputPoints[0:3]
            Femur3JGM=inputPoints[3:6]
            Femur2JGM1,Femur3JGM1,FtransTmp=self.getDisByPlane(Femur2JGM,Femur3JGM)
            FtransList.append(FtransTmp)
            #d1为假体第三刀最上方的点到对应骨骼指定最高点所在平面的距离
            dd=(Femur3JGM1[0][2]+Femur3JGM1[1][2])/2-(femurUpMean-4)
            if dd>0:
                d1=abs(dd)*3
            else:
                d1=abs(dd)
            #d2及d3为后髁点到第三刀接骨面的距离
            d2=abs(abs(self.point2area_distance(np.array(Femur3JGM1), point3))-7)
            d3=abs(abs(self.point2area_distance(np.array(Femur3JGM1), point2))-7)
            #d4为假体第三刀最上方的点到股骨最近点的距离
            d4=abs(self.getDistance(Femur3JGM1[0].copy()))+abs(self.getDistance(Femur3JGM1[1].copy()))
            #d5为假体后髁点到股骨后髁点的距离
            #对point2及point3进行变换
            point21=np.dot(FtransTmp,[point2[0],point2[1],point2[2],1])[0:3]
            point31=np.dot(FtransTmp,[point3[0],point3[1],point3[2],1])[0:3]
            d5=0#self.getPointToPlane(point21,planePoints[i],np.array([0,1,0]))+self.getPointToPlane(point31,planePoints[i],np.array([0,1,0]))
            #d6为假体第二刀最上方的点到股骨最近点的距离
            d6=abs(self.getDistance(Femur2JGM1[0].copy()))+abs(self.getDistance(Femur2JGM1[1].copy()))
            diffList.append(d1+d2+d3+d4+d5*0.5+d6*2)
            # print('d1:',d1,'d2:',d2,'d3:',d3,'d4:',d4,'d5:',d5,'d6:',d6)

        print(diffList)
        self.minIndex=diffList.index(min(diffList))
        FtransTmp=FtransList[self.minIndex]
        
        self.FemurYueshuMatrix = FtransTmp
        Name = 'femur-' + self.judge + list3[self.minIndex]
        # self.ui.JiaTiName.setText(Name)
        self.jiatiload=self.minIndex
        #旋转90
        Ftrans1 = np.array([[1, 0, 0, 0],
            [0, 0, -1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1]])
        newTrans=np.dot(Ftrans1,FtransTmp)
        self.HardModel(newTrans)
        if self.judge == 'L':
            #对targetModel进行X方向的镜像处理
            Ftrans = np.array([[-1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
            transform = vtk.vtkTransform()
            transform.SetMatrix(Ftrans.flatten())
            transform.Update()
            transform_filter = vtk.vtkTransformPolyDataFilter()
            transform_filter.SetInputData(self.polydata)
            transform_filter.SetTransform(transform)
            transform_filter.Update()
            #计算法向量，并反转
            normal = vtk.vtkPolyDataNormals()
            normal.SetInputData(transform_filter.GetOutput())
            normal.FlipNormalsOn()
            normal.Update()
            points22222222=[]
            self.polydata = normal.GetOutput()
            FemurPoints = ['开髓点1', '内侧凹点1', '外侧凸点1', '内侧远端1', '外侧远端1', '内侧后髁1', '外侧后髁1', '外侧皮质高点1', 'A点1', "股骨头球心1","H点1"]
            for i in range(len(FemurPoints)):
                PointNode=self.myScene.getMarkupsByName(FemurPoints[i])
                point = PointNode.getPoints()[0]
                point = [point[0], point[1], point[2], 1]
                PointNode.RemoveAllPoints()
                pNew=np.dot(newTrans, point)[0:3]
                pNew[0]=-pNew[0]
                PointNode.AddPoints(pNew)
                points22222222.append(pNew)
            #markupsNode.AddControlPoint(np.dot(FtransTmp, point)[0:3])
        else:
            FemurPoints = ['开髓点1', '内侧凹点1', '外侧凸点1', '内侧远端1', '外侧远端1', '内侧后髁1', '外侧后髁1', '外侧皮质高点1', 'A点1', "股骨头球心1","H点1"]
            for i in range(len(FemurPoints)):
                PointNode=self.myScene.getMarkupsByName(FemurPoints[i])
                point = PointNode.getPoints()[0]
                point = [point[0], point[1], point[2], 1]
                PointNode.RemoveAllPoints()
                PointNode.AddPoints(np.dot(newTrans, point)[0:3])
        self.polydata=self.cropModel(self.polydata, [0, 80, 0], [0, -1, 0])
        writer = vtk.vtkSTLWriter()

        writer.SetFileName(self.outPutPath + '/Femur111.stl')
        writer.SetInputData(self.polydata)
        writer.Write()
        writer.SetFileName(self.outPutPath + '/Femur222.stl')
        writer.SetInputData(self.polydata)
        writer.Write()
        #markupsNode=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','P')

        #self.updateLowPoints(newTrans,1)

    #通过平面对模型进行裁剪
    def cropModel(self,targetModel, planeOrigin, planeNormal):
        # 裁剪
        plane = vtk.vtkPlane()
        plane.SetOrigin(planeOrigin)
        plane.SetNormal(planeNormal)

        planeCollection = vtk.vtkPlaneCollection()
        planeCollection.AddItem(plane)

        clipper = vtk.vtkClipClosedSurface()
        clipper.SetInputData(targetModel)
        clipper.SetClippingPlanes(planeCollection)
        clipper.Update()
        # 输出
        return clipper.GetOutput()

    #确定胫骨截骨面，并正确放置假体位置     
    def TibiaJieGu(self):
        # 胫骨截骨面
        TibiaJieGu = self.myScene.AddMarkups('胫骨截骨面')
        TibiaJieGu.AddPoints([30, 0, 0])
        TibiaJieGu.AddPoints([0, 30, 0])
        TibiaJieGu.AddPoints([0, 0, 0])
        point=self.myScene.getMarkupsByName('内侧高点1').getPointsWorld()[0]
        point1=self.myScene.getMarkupsByName('外侧高点1').getPointsWorld()[0]
        point3=self.myScene.getMarkupsByName('胫骨隆凸1').getPointsWorld()[0]
        TibiaJGM = self.myScene.getMarkupsByName('胫骨截骨面').getPointsWorld()
        pointTouYing = np.array(self.TouYing(np.array(TibiaJGM),point))



        xiangliang=(point-pointTouYing)[0:3]
        z=[0,0,1]
        x=np.dot(xiangliang,z)

        print('x',x)
        d = self.point2area_distance(np.array(TibiaJGM), point)
        print('d:',d)
        if x > 0:
            d = -d
        distance = 6 + d

        


        if self.judge == 'L':
            angle_point=(np.array(point1)-point)[0:2]
        else:
            angle_point=(np.array(point)-point1)[0:2]

        angle=self.Angle(angle_point,[1,0])
        print("angle:",angle)
        if(angle>90):
            angle=180-angle
        if(np.dot(angle_point,[0,1])<0):
            angle=-angle
        trans_angle=self.GetMarix_z(angle)

        point2 = [(point[0]+point1[0]+point3[0])/3,(point[1]+point1[1])/2,(point[2]+point1[2]+point3[2])/3]
        #a = [point2[0] - point3[0], point2[1] - point3[1], point2[2] - point3[2]]
        TransformTmp =self.myScene.getTransformByName('变换_胫骨约束')
        # if slicer.modules.NoImageWelcomeWidget.judge == 'R':
        #   a[0]=-a[0]
        #   a[1] = -a[1]
        TtransTmp = np.array([[1, 0, 0, -point2[0]],
                        [0, 1, 0, -point2[1]-5],
                        [0, 0, 1, distance],
                        [0, 0, 0, 1]])

        #print('TtransTmp',TtransTmp,'a',a)
        #xzjz = self.GetMarix_z(-2)
        trans = np.dot(TtransTmp,trans_angle)
        TransformTmp.matrix=trans
        Ftransform11 = self.myScene.getTransformByName('变换_胫骨约束').matrix
        Ftrans1 = np.array([[-1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        trans_femur = np.dot(Ftrans1, np.dot(Ftransform11, Ftrans1))
        self.HardModel(self.FilePath + '/Tibia1.stl', trans_femur)
        trans=np.dot(Ftransform11,self.WordToReal)
        # 将所有点复制出一份放到截骨调整中
        TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
        for i in range(len(TibiaPoints)):
            PointNode = self.myScene.getMarkupsByName(TibiaPoints[i] + "1")
            point = self.myScene.getMarkupsByName(TibiaPoints[i]).getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.RemoveAllPoints()
            PointNode.AddPoints(np.dot(trans, point)[0:3])
       
        Ftrans = np.array([[1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        TransformTmp.matrix=Ftrans

        #self.onJieGuJianXi()


    #推荐胫骨假体
    def SelectTibiaJiaTi(self):
        self.TibiaJieGu()
        PointPath="static/asset/ssm/假体库/a"
        list = ['1-5', '2', '2-5', '3', '4', '5']
        dis=DistanceCaculate()
        dis.initLocator('Tibia')

        disList=[]
        diffList=[]
        for i in range(0, len(list)):
            inputPoints=[]
            name = 'Tibia-' + list[i]
            lujing = os.path.join(PointPath,name+'.txt')
            print('lujing',lujing)
            point  =  np.loadtxt(lujing)
            judge=1
            if dis.getDistance([0,0,0])>0:
                judge=-1
            dis1=0
            for j in range(3):
                dis1=dis1+dis.getDistance(point[j])*judge
            dis1=dis1/3
            diffList.append(dis1)
            pointtmp=point.copy()
            pointtmp[:,1]=pointtmp[:,1]-dis1

            d1=dis.getDistance(pointtmp[3])*judge
            if d1>0:
                d1=d1*1.5
            d2=dis.getDistance(pointtmp[4])*judge
            if d2>0:
                d2=d2*1.5
            dis2=d1+d2
            d1=dis.getDistance(pointtmp[5])*judge
            if d1>0:
                d1=d1*1.5
            d2=dis.getDistance(pointtmp[6])*judge
            if d2>0:
                d2=d2*1.5
            dis3=d1+d2
            
            disEnd=abs(dis2/2)+abs(dis3/2)
            disList.append(disEnd)

        self.jiatiload='Tibia-' + list[disList.index(min(disList))]
        Ftransform11 = np.array([[1, 0, 0, 0],
                    [0, 1, 0, diffList[disList.index(min(disList))]],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])


        Ftrans1 = np.array([[-1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        trans_femur = np.dot(Ftrans1, np.dot(Ftransform11, Ftrans1))
        self.HardModelSelf(self.FilePath + '/Tibia11.stl', trans_femur)
        # 将所有点复制出一份放到截骨调整中
        TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
        for i in range(len(TibiaPoints)):
            PointNode = self.myScene.getMarkupsByName(TibiaPoints[i] + "1")
            point = PointNode.getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.RemoveAllPoints()
            PointNode.AddPoints(np.dot(Ftransform11, point)[0:3])
       

    # 对约束进行微调
    def loaddier(self):
        # 第二刀截骨面
 
        Ftransform11 = self.myScene.getTransformByName('变换_股骨约束').matrix
        Ftrans1 = np.array([[-1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        Ftrans2 = np.array([[1, 0, 0, 0],
                    [0, 0, -1, 0],
                    [0, 1, 0, 0],
                    [0, 0, 0, 1]])
        trans_femur = np.dot(Ftrans1, np.dot(Ftransform11, Ftrans1))
        world = np.dot(Ftrans2, Ftransform11)
        self.HardModel(self.FilePath + '/Femur1.stl', trans_femur)

        FemurPoints = ['开髓点', '内侧凹点', '外侧凸点', '内侧远端', '外侧远端', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点', "股骨头球心",'H点']
        for i in range(len(FemurPoints)):
            PointNode = self.myScene.getMarkupsByName(FemurPoints[i] + "1")
            point = self.myScene.getMarkupsByName(FemurPoints[i]+ "1").getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.RemoveAllPoints()
            PointNode.AddPoints(np.dot(world, point)[0:3])

        Ftrans = np.array([[1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        self.myScene.getTransformByName('变换_股骨约束').matrix=Ftrans



    def define_area(self, a):
        point1 = a[0]
        point2 = a[1]
        point3 = a[2]
        AB = np.asmatrix(point2 - point1)
        AC = np.asmatrix(point3 - point1)
        N = np.cross(AB, AC)  # 向量叉乘，求法向量
        # Ax+By+Cz
        Ax = N[0, 0]
        By = N[0, 1]
        Cz = N[0, 2]
        D = -(Ax * point1[0] + By * point1[1] + Cz * point1[2])
        return Ax, By, Cz, D

    # 点到面的距离
    def point2area_distance(self, a, point4):
        Ax, By, Cz, D = self.define_area(a)
        mod_d = Ax * point4[0] + By * point4[1] + Cz * point4[2] + D
        mod_area = np.sqrt(np.sum(np.square([Ax, By, Cz])))
        d = abs(mod_d) / mod_area
        return d


    # 获得投影点（a为三个点确定的平面，point为要获得投影点的点）
    def TouYing(self, a, point):
        Ax, By, Cz, D = self.define_area(a)
        k = (Ax * point[0] + By * point[1] + Cz * point[2] + D) / (np.sum(np.square([Ax, By, Cz])))
        b = [point[0] - k * Ax, point[1] - k * By, point[2] - k * Cz]
        return b

    # 求角度-传递两个向量（求两个向量的夹角）
    def Angle(self, xiangliang1, xiangliang2):
        import math
        cosa = np.dot(xiangliang1, xiangliang2)/math.sqrt(np.dot(xiangliang1,xiangliang1))/math.sqrt(np.dot(xiangliang2, xiangliang2))
        a = math.degrees(math.acos(cosa))
        return a
    
    #旋转角度变换
    def GetMarix(self,trans,jd,point):
        import math
        jd = math.radians(jd)
        trans_ni=np.linalg.inv(trans)
        Tjxlx=[1,0,0]
        xzjz = [[math.cos(jd) + Tjxlx[0] * Tjxlx[0] * (1 - math.cos(jd)),
                    -Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[1] * Tjxlx[1] * (1 - math.cos(jd)),
                    -Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [-Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)),
                    Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[2] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [0, 0, 0, 1]]
        
        point=np.array([point[0],point[1],point[2],1])
        point_tmp1=np.dot(trans_ni,point)
        point_tmp2=np.dot(xzjz,point_tmp1)
        point=np.dot(trans,point_tmp2)
        return point[0:3]

    def GetMarix_z(self,jd):
        import math
        jd = math.radians(jd)
        Tjxlx=[0,0,1]
        xzjz = np.array([[math.cos(jd) + Tjxlx[0] * Tjxlx[0] * (1 - math.cos(jd)),
                    -Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[1] * Tjxlx[1] * (1 - math.cos(jd)),
                    -Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [-Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)),
                    Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[2] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [0, 0, 0, 1]])
        return xzjz

    def GetMarix_x(self,jd):
            jd = math.radians(jd)
            Tjxlx=[1,0,0]
            xzjz = np.array([[math.cos(jd) + Tjxlx[0] * Tjxlx[0] * (1 - math.cos(jd)),
                        -Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                        Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                    [Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                        math.cos(jd) + Tjxlx[1] * Tjxlx[1] * (1 - math.cos(jd)),
                        -Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                    [-Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)),
                        Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)),
                        math.cos(jd) + Tjxlx[2] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                    [0, 0, 0, 1]])
            return xzjz
   




class ssmTibia:
    def __init__(self):
        self.Femur_list = None
        self.judge = None
        self.femurOrTibia = None
        self.polydata=None
        self.pointsOut = None
        self.pointsInner = None
        self.FilePath = "static/asset/ssm"
        self.outPutPath = "static/output/ssm"
        self.myScene = MyVTKScene()

    def initLocator(self,filename):
        #如果是stl文件
        if filename.endswith('.stl'):                
            reader = vtk.vtkSTLReader()
            reader.SetFileName(filename)
            reader.Update()
        elif filename.endswith('.vtk'):
            reader = vtk.vtkPolyDataReader()
            reader.SetFileName(filename)
            reader.Update()
        elif filename.endswith('.ply'):
            reader = vtk.vtkPLYReader()
            reader.SetFileName(filename)
            reader.Update()

        self.polydata = reader.GetOutput()
        self.locator = vtk.vtkImplicitPolyDataDistance()
        self.locator.SetInput(self.polydata)
    def updateLocator(self):
        self.locator.SetInput(self.polydata)



    def getDistance(self,point):
        point[0]=-point[0]
        point[1]=-point[1]
        closestPointOnSurface_World = np.zeros(3)
        d=self.locator.EvaluateFunctionAndGetClosestPoint(point,closestPointOnSurface_World)
        return -d
    
    def getClosestPoint(self,point):
        point[0]=-point[0]
        point[1]=-point[1]
        closestPointOnSurface_World = np.zeros(3)
        d=self.locator.EvaluateFunctionAndGetClosestPoint(point,closestPointOnSurface_World)
        closestPointOnSurface_World[0]=-closestPointOnSurface_World[0]
        closestPointOnSurface_World[1]=-closestPointOnSurface_World[1]
        return closestPointOnSurface_World

    def getPolyDataPointsByIndex(self,index):
        point = self.polydata.GetPoint(index)
        point=[point[0],point[1],point[2]]
        point[0]=-point[0]
        point[1]=-point[1]
        return point





    def remeshModel(self,path):
        # 读取输入的模型文件
        reader = vtk.vtkSTLReader()
        reader.SetFileName(path)
        reader.Update()
        smoothFilter = vtk.vtkSmoothPolyDataFilter()
        smoothFilter.SetInputData(reader.GetOutput())



        # 设置平滑迭代次数为20次
        smoothFilter.SetNumberOfIterations(20)

        # 设置平滑因子（SmoothFactor）为0.1
        smoothFilter.SetRelaxationFactor(0.08)
        smoothFilter.Update()
        # tri_filter = vtk.vtkTriangleFilter()
        # tri_filter.SetInputData(smoothFilter.GetOutput())
        # tri_filter.Update()
        # inputMesh = pv.wrap(tri_filter.GetOutput())
        # clus = pyacvd.Clustering(inputMesh)

        # clus.subdivide(2)
        # clus.cluster(5000)
        # outputMesh = vtk.vtkPolyData()
        # outputMesh.DeepCopy(clus.create_mesh())
        # 保存重构后的表面模型
        writer = vtk.vtkSTLWriter()
        writer.SetFileName(path)
        writer.SetInputData(smoothFilter.GetOutput())
        writer.Write()



    def scaleModel(self,inputPath,scaleX=1.0, scaleY=1.0, scaleZ=1.0):
        """Mesh relaxation based on vtkWindowedSincPolyDataFilter.
        Scale of 1.0 means original size, >1.0 means magnification.
        """
        reader = vtk.vtkPolyDataReader()
        reader.SetFileName(inputPath)
        reader.Update()
        model = reader.GetOutput()
        transform = vtk.vtkTransform()
        transform.Scale(scaleX, scaleY, scaleZ)
        transformFilter = vtk.vtkTransformFilter()
        transformFilter.SetInputData(model)
        transformFilter.SetTransform(transform)

        if transform.GetMatrix().Determinant() >= 0.0:
            transformFilter.Update()
            writer = vtk.vtkSTLWriter()
            writer.SetFileName(inputPath.replace('.vtk', '.stl'))
            writer.SetInputData(transformFilter.GetOutput())
            writer.Write()

    def registion(self,points_From, points_To):
        if len(points_From)!=len(points_To):
            return
        fix_point = vtk.vtkPoints()
        fix_point.SetNumberOfPoints(len(points_From))
        mov_point = vtk.vtkPoints()
        mov_point.SetNumberOfPoints(len(points_From))
        for i in range(len(points_From)):
            mov_point.SetPoint(i, points_From[i][0], points_From[i][1], points_From[i][2])
            fix_point.SetPoint(i, points_To[i][0], points_To[i][1], points_To[i][2])
            
        fix_point.Modified()
        mov_point.Modified()
        landmarkTransform = vtk.vtkLandmarkTransform()
        landmarkTransform.SetModeToRigidBody()
        landmarkTransform.SetSourceLandmarks(mov_point)
        landmarkTransform.SetTargetLandmarks(fix_point)

        landmarkTransform.Update()
        trans = np.zeros((4, 4))
        for i in range(4):
            for j in range(4):
                trans[i][j] = landmarkTransform.GetMatrix().GetElement(i, j)
        return trans

    def startGuihua(self):
        pass

    def preparPointsForTibiaGuihua(self,points):
        points=np.array(points)
        self.TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘']
        for i in range(len(self.TibiaPoints)):
            point = self.myScene.AddMarkups(self.TibiaPoints[i])
            point.AddPoints(points[i].copy())

        point1 = self.myScene.AddMarkups('踝穴中心')
        point1.AddPoints((points[9].copy()+points[10].copy())/2)


    def prparModel(self,path):
        self.initLocator(path)



    def preparPoints_tibia(self):
        Points = self.Femur_list[0:11]
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        self.Femur_list = np.delete(self.Femur_list, 9, 0)
        self.TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘']

        self.keypoints = Points[0:9].copy()
        for i in range(len(self.keypoints)):
            point = self.myScene.AddMarkups(self.TibiaPoints[i])
            point.AddPoints(self.keypoints[i].copy())
        point1 = self.myScene.AddMarkups('踝穴中心')
        point1.AddPoints((Points[9]+Points[10])/2)
        if self.judge == 'L':
            self.keypoints[:, 0] = -self.keypoints[:, 0]
            self.Femur_list[:, 0] = -self.Femur_list[:, 0]

    def HardModel(self, trans):
        # Apply the transformation to the model
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        transformation = np.dot(np.dot(Ftrans1, trans), Ftrans1)
        transform_filter = vtk.vtkTransformPolyDataFilter()
        transform = vtk.vtkTransform()
        transform.SetMatrix(trans.flatten())
        transform_filter.SetTransform(transform)
        transform_filter.SetInputData(self.polydata)
        transform_filter.Update()
        self.polydata = transform_filter.GetOutput()

    def HardModel1(self, path1, trans):
        if "vtk" in path1:
            reader = vtk.vtkPolyDataReader()
            reader.SetFileName(path1)
            path1=path1.replace("vtk", "stl")
        else:
            reader = vtk.vtkSTLReader()
            reader.SetFileName(path1)

        reader.Update()
        model = reader.GetOutput()
        # Define the transformation
        transformation = trans
        # Apply the transformation to the model
        transform_filter = vtk.vtkTransformFilter()
        transform = vtk.vtkTransform()
        transform.SetMatrix(transformation.flatten())
        transform_filter.SetTransform(transform)
        transform_filter.SetInputData(model)
        transform_filter.Update()

        # # 创建平面
        # if "Femur" in path1:
        #     # 创建平面
        #     plane = vtk.vtkPlane()
        #     plane.SetOrigin(0, 0, 79)  # 平面的原点
        #     plane.SetNormal(0, 0, -1)  # 平面的法向量
        # else:
        #     plane = vtk.vtkPlane()
        #     plane.SetOrigin(0, 0, -79)  # 平面的原点
        #     plane.SetNormal(0, 0, 1)  # 平面的法向量


        # normals = vtk.vtkPolyDataNormals()
        # normals.SetInputData(transform_filter.GetOutput())
        # normals.ComputePointNormalsOn()
        # normals.ComputeCellNormalsOff()
        # normals.AutoOrientNormalsOn()
        # normals.ConsistencyOn()
        # normals.Update()

        # colors = vtk.vtkNamedColors()
        # planes=vtk.vtkPlaneCollection()
        # planes.AddItem(plane)
        # clipper = vtk.vtkClipClosedSurface()
        # clipper.SetInputData(normals.GetOutput())  # 设置输入数据
        # clipper.SetActivePlaneId(0)
        # clipper.SetClippingPlanes(planes)  # 设置切割平面
        # clipper.SetScalarModeToColors()
        # clipper.SetClipColor(colors.GetColor3d("Banana"))
        # clipper.SetBaseColor(colors.GetColor3d("Tomato"))
        # clipper.SetActivePlaneColor(colors.GetColor3d("SandyBrown"))
        # clipper.Update()



        writer = vtk.vtkSTLWriter()
        writer.SetFileName(path1)
        writer.SetInputData(transform_filter.GetOutput())
        writer.Write()



    def onGuGuTouConfirm(self,points):
        points = points.astype(np.float64)  # 防止溢出
        num_points = points.shape[0]
        print(num_points)
        x = points[:, 0]
        y = points[:, 1]
        z = points[:, 2]
        x_avr = sum(x) / num_points
        y_avr = sum(y) / num_points
        z_avr = sum(z) / num_points
        xx_avr = sum(x * x) / num_points
        yy_avr = sum(y * y) / num_points
        zz_avr = sum(z * z) / num_points
        xy_avr = sum(x * y) / num_points
        xz_avr = sum(x * z) / num_points
        yz_avr = sum(y * z) / num_points
        xxx_avr = sum(x * x * x) / num_points
        xxy_avr = sum(x * x * y) / num_points
        xxz_avr = sum(x * x * z) / num_points
        xyy_avr = sum(x * y * y) / num_points
        xzz_avr = sum(x * z * z) / num_points
        yyy_avr = sum(y * y * y) / num_points
        yyz_avr = sum(y * y * z) / num_points
        yzz_avr = sum(y * z * z) / num_points
        zzz_avr = sum(z * z * z) / num_points

        A = np.array([[xx_avr - x_avr * x_avr, xy_avr - x_avr * y_avr, xz_avr - x_avr * z_avr],
                    [xy_avr - x_avr * y_avr, yy_avr - y_avr * y_avr, yz_avr - y_avr * z_avr],
                    [xz_avr - x_avr * z_avr, yz_avr - y_avr * z_avr, zz_avr - z_avr * z_avr]])
        b = np.array([xxx_avr - x_avr * xx_avr + xyy_avr - x_avr * yy_avr + xzz_avr - x_avr * zz_avr,
                    xxy_avr - y_avr * xx_avr + yyy_avr - y_avr * yy_avr + yzz_avr - y_avr * zz_avr,
                    xxz_avr - z_avr * xx_avr + yyz_avr - z_avr * yy_avr + zzz_avr - z_avr * zz_avr])
        # print(A, b)
        b = b / 2
        center = np.linalg.solve(A, b)
        x0 = center[0]
        y0 = center[1]
        z0 = center[2]
        r2 = xx_avr - 2 * x0 * x_avr + x0 * x0 + yy_avr - 2 * y0 * y_avr + y0 * y0 + zz_avr - 2 * z0 * z_avr + z0 * z0
        r = r2 ** 0.5
        print(center, r)
        return center


    # 建立股骨坐标系，股骨头球心，开髓点，外侧凸点，内侧凹点
    def creatCordingnate_femur(self):
        ras1 = self.myScene.getMarkupsByName('股骨头球心').getPoints()[0]
        ras2 = self.myScene.getMarkupsByName('开髓点').getPoints()[0]
        ras3 = self.myScene.getMarkupsByName('外侧凸点').getPoints()[0]
        ras4 = self.myScene.getMarkupsByName('内侧凹点').getPoints()[0]
        zb1 = [ras1[0], ras1[1], ras1[2]]  # 坐标1，球心
        zb2 = [ras2[0], ras2[1], ras2[2]]  # 坐标2，原点
        zb3 = [ras3[0], ras3[1], ras3[2]]  # 坐标3，左侧点
        zb4 = [ras4[0], ras4[1], ras4[2]]  # 坐标4，右侧点
        jxlz = [0, 0, 0]  # Y轴基向量
        for i in range(0, 3):
            jxlz[i] = zb1[i]-zb2[i]
        moz = np.sqrt(np.square(jxlz[0]) + np.square(jxlz[1]) + np.square(jxlz[2]))  # 基向量z的模
        for i in range(0, 3):
            jxlz[i] = jxlz[i] / moz
        csD = jxlz[0] * zb2[0] + jxlz[1] * zb2[1] + jxlz[2] * zb2[2]  # 平面方程参数D
        csT3 = (jxlz[0] * zb3[0] + jxlz[1] * zb3[1] + jxlz[2] * zb3[2] - csD) / (
                jxlz[0] * jxlz[0] + jxlz[1] * jxlz[1] + jxlz[2] * jxlz[2])  # 坐标3平面方程参数T
        ty3 = [0, 0, 0]  # 坐标3在YZ平面的投影
        for i in range(0, 3):
            ty3[i] = zb3[i] - jxlz[i] * csT3
        csT4 = (jxlz[0] * zb4[0] + jxlz[1] * zb4[1] + jxlz[2] * zb4[2] - csD) / (
                jxlz[0] * jxlz[0] + jxlz[1] * jxlz[1] + jxlz[2] * jxlz[2])
        ty4 = [0, 0, 0]
        for i in range(0, 3):
            ty4[i] = zb4[i] - jxlz[i] * csT4
        jxlx = [0, 0, 0]  # X轴基向量
        for i in range(0, 3):  #########判断左右腿
            # if self.judge == 'L':
            #     jxlx[i] = ty3[i] - ty4[i]
            # else:
            jxlx[i] = ty4[i] - ty3[i]
        mox = np.sqrt(np.square(jxlx[0]) + np.square(jxlx[1]) + np.square(jxlx[2]))  # 基向量X的模
        for i in range(0, 3):
            jxlx[i] = jxlx[i] / mox
        jxly = [0, 0, 0]  # y轴基向量
        jxly[0] = (jxlx[1] * jxlz[2] - jxlx[2] * jxlz[1])
        jxly[1] = (jxlx[2] * jxlz[0] - jxlx[0] * jxlz[2])
        jxly[2] = (jxlx[0] * jxlz[1] - jxlx[1] * jxlz[0])
        moy = np.sqrt(np.square(jxly[0]) + np.square(jxly[1]) + np.square(jxly[2]))  # 基向量y的模
        for i in range(0, 3):
            jxly[i] = jxly[i] / moy

        cord = np.zeros((4, 4))
        cord[0:3, 0] = jxlx
        cord[0:3, 1] = jxly
        cord[0:3, 2] = jxlz
        cord[0:3, 3] = zb2
        cord[3, 3] = 1
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        Ftrans3 = np.dot(Ftrans1,np.linalg.inv(cord))
        FemurHardTrans = Ftrans3
        # Ftrans1 = np.array([[-1, 0, 0, 0],
        #                     [0, -1, 0, 0],
        #                     [0, 0, 1, 0],
        #                     [0, 0, 0, 1]])
        # FemurHardTrans = np.dot(np.dot(Ftrans1, FemurHardTrans), Ftrans1)
        # word = np.dot(np.dot(Ftrans1, FemurHardTrans), Ftrans1)
        self.HardModel(FemurHardTrans)
        self.updateLocator()
        # writer = vtk.vtkSTLWriter()
        # writer.SetFileName("d:/Data/Femur.stl")
        # writer.SetInputData(self.polydata)
        # writer.Write()
        FemurPoints = ['开髓点', '内侧凹点', '外侧凸点', '内侧远端', '外侧远端', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点', "股骨头球心", "femurUp1", "femurUp2"]
        for i in range(len(FemurPoints)):
            PointNode = self.myScene.AddMarkups(FemurPoints[i] + "1")
            point = self.myScene.getMarkupsByName(FemurPoints[i]).getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.AddPoints(np.dot(Ftrans3, point)[0:3])
        self.updateLowPoints(Ftrans3)

        print(FemurHardTrans)


    def updateLowPoints(self,trans):
        for i in range(len(self.pointsOut)):
            self.pointsOut[i]=(np.dot(trans, [self.pointsOut[i][0], self.pointsOut[i][1], self.pointsOut[i][2], 1])[0:3])

        for i in range(len(self.pointsInner)):
            self.pointsInner[i]=(np.dot(trans,[self.pointsInner[i][0],self.pointsInner[i][1],self.pointsInner[i][2],1])[0:3])
        self.pointsInner=list(self.pointsInner)
        self.pointsOut=list(self.pointsOut)
        #获取pointsInnerZ轴最低点
        self.pointsInner.sort(key=lambda x:x[2])
        self.pointsOut.sort(key=lambda x:x[2])
        point = self.myScene.getMarkupsByName('内侧远端1')
        point.RemoveAllPoints()
        point.AddPoints(self.pointsInner[0])
        point = self.myScene.getMarkupsByName('外侧远端1')
        point.RemoveAllPoints()
        point.AddPoints(self.pointsOut[0])

        #获取pointsInnerY轴最低点
        self.pointsInner.sort(key=lambda x:x[1])
        self.pointsOut.sort(key=lambda x:x[1])
        point = self.myScene.getMarkupsByName('内侧后髁1')

        point.RemoveAllPoints()
        point.AddPoints(self.pointsInner[0])
        point = self.myScene.getMarkupsByName('外侧后髁1')
        print(self.pointsOut[0])
        print(point.getPoints()[0])
        point.RemoveAllPoints()
        point.AddPoints(self.pointsOut[0])

    def project_point_to_plane(self,point, plane_point, plane_normal):
        """
        计算点到平面的投影点。

        参数:
        point (np.array): 要投影的点，形如 [x, y, z]。
        plane_point (np.array): 平面上的一点，形如 [x, y, z]。
        plane_normal (np.array): 平面的法向量，形如 [nx, ny, nz]。

        返回:
        np.array: 投影点，形如 [x, y, z]。
        """
        # 将输入转换为 numpy 数组
        point = np.array(point)
        plane_point = np.array(plane_point)
        plane_normal = np.array(plane_normal)
        
        # 计算点到平面的向量
        point_to_plane = point - plane_point
        
        # 计算点到平面的距离
        distance = np.dot(point_to_plane, plane_normal) / np.linalg.norm(plane_normal)
        
        # 计算投影点
        projection = point - distance * plane_normal / np.linalg.norm(plane_normal)
        
        return projection



    def creatCordingnate_tibia(self):

        ras1 = self.myScene.getMarkupsByName('胫骨隆凸').getPoints()[0]
        ras2 = self.myScene.getMarkupsByName('胫骨结节').getPoints()[0]
        ras3 = self.myScene.getMarkupsByName('踝穴中心').getPoints()[0]
        ras4 = self.myScene.getMarkupsByName('内侧边缘').getPoints()[0]
        ras5 = self.myScene.getMarkupsByName('外侧边缘').getPoints()[0]
        Tjxlz=(ras1-ras3)/np.linalg.norm(ras1-ras3)
        ras4Pro=self.project_point_to_plane(ras4,ras1,Tjxlz)
        ras5Pro=self.project_point_to_plane(ras5,ras1,Tjxlz)

        Tjxlx=(ras5Pro-ras4Pro)/np.linalg.norm(ras5Pro-ras4Pro)

        Tjxly=np.cross(Tjxlx,Tjxlz)
        Tjxly=Tjxly/np.linalg.norm(Tjxly)

        Tjxlx=np.cross(Tjxly,Tjxlz)
        Tjxlx=Tjxlx/np.linalg.norm(Tjxlx)



        Ttrans2 = np.array([[float(Tjxlx[0]), float(Tjxly[0]), float(Tjxlz[0]), ras1[0]],
                                [float(Tjxlx[1]), float(Tjxly[1]), float(Tjxlz[1]), ras1[1]],
                                [float(Tjxlx[2]), float(Tjxly[2]), float(Tjxlz[2]), ras1[2]],
                                [0, 0, 0, 1]])

        Ttrans4 = np.array([[1, 0, 0, 0],
                            [0, 1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        

        Ttrans2=np.linalg.inv(Ttrans2)
        print("Ttrans2",Ttrans2)
        Ftransform1 = self.myScene.AddTransform('变换_胫骨临时', Ttrans2)
        Ftransform11 = self.myScene.AddTransform('变换_胫骨约束', Ttrans4)
        Ftransform12 = self.myScene.AddTransform('变换_胫骨调整', Ttrans4)
        Ftransform12.parent = Ftransform11
        print("self.Ttrans3",Ttrans2)


        self.TibiaHardTrans =Ttrans2
        Ftrans1 = np.array([[-1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, 1, 0],
                            [0, 0, 0, 1]])
        self.TibiaHardTrans=np.dot(self.TibiaHardTrans, Ftrans1)
        self.WordToReal = np.dot(Ftrans1, Ttrans2)
        #self.TibiaHardTrans = np.dot(Ftrans1, self.TibiaHardTrans)
        #self.TibiaHardTrans = np.dot(Ftrans1, np.dot(self.TibiaHardTrans, Ftrans1))
        #print("self.Ftrans2", self.Ftrans2)
        #print("self.Ftrans3",self.Ftrans3)
        self.HardModel(self.TibiaHardTrans)
        #model=slicer.util.loadModel(self.FilePath + '/Tibia1.stl')
        writer = vtk.vtkSTLWriter()
        writer.SetFileName(self.FilePath + '/Tibia1.stl')
        writer.SetInputData(self.polydata)
        writer.Write()
        
        
        
        
        # 将所有点复制出一份放到截骨调整中
        TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
        for i in range(len(TibiaPoints)):
            PointNode = self.myScene.AddMarkups(TibiaPoints[i] + "1")
            point = self.myScene.getMarkupsByName(TibiaPoints[i]).getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.AddPoints(np.dot(self.WordToReal, point)[0:3])
            PointNode.parent = self.myScene.getTransformByName('变换_胫骨调整')



      
    # 获取变换下的截骨面
    def GetTransPoint(self, name):
        if name == "股骨第一截骨面":
            p1 = self.GetTransPoint_real([15.063, 25, 0])
            p2 = self.GetTransPoint_real([0, 0, 0])
            p3 = self.GetTransPoint_real([-21.372, -23.271, 0])

        elif name == "股骨第二截骨面":
            p1 = self.GetTransPoint_real([-15.063, 23.063, 22.222])
            p2 = self.GetTransPoint_real([1.143, 23.207, 29.894])
            p3 = self.GetTransPoint_real([21.372, 23.271, 24.171])
        zb = np.array([p1, p2, p3])
        return zb

    def FirstJieGu(self):
        # 先将传过来的点，变换之原点，再变换至调整下
        point = self.myScene.getMarkupsByName('内侧远端1').getPointsWorld()[0]
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0]

        # 外侧皮质高点1'
        PointNode = self.myScene.AddMarkups('股骨第一截骨面')
        PointNode.AddPoints([30.951, -14.145, 17.976])
        PointNode.AddPoints([-31.236, -1.339, 17.976])
        PointNode.AddPoints([-31.485, -15.010, 17.976])
        PointNode.parent = self.myScene.getTransformByName("变换_股骨假体调整")

        PointNode = self.myScene.AddMarkups('股骨第二截骨面')
        PointNode.AddPoints([-16.637, 24.306-9, 21.857+18])
        PointNode.AddPoints([1.185, 25.471-9, 32.778+18])
        PointNode.AddPoints([22.742, 24.575-9, 24.382+18])
        PointNode.parent = self.myScene.getTransformByName("变换_股骨假体调整")

        Femur1JGM = self.myScene.getMarkupsByName('股骨第一截骨面').getPointsWorld()
        Femur2JGM = self.myScene.getMarkupsByName('股骨第二截骨面').getPointsWorld()
        d = self.point2area_distance(np.array(Femur1JGM), point)
        d1 = self.point2area_distance(np.array(Femur2JGM), point1)
        self.destance = d - 8
        FtransTmp = np.array([[1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, self.destance],
                    [0, 0, 0, 1]])
        self.myScene.getTransformByName("变换_股骨约束").matrix = FtransTmp
        ras1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0]
        d = self.point2area_distance(np.array(Femur2JGM), ras1)
        x = d / math.cos(math.radians(6))
        n1=[0,1,0]
        n2 = np.array(ras1) - self.TouYing(Femur2JGM, ras1)
        if np.dot(n1,n2)<0:
            direction = 1
        else:
            direction = -1
        x=direction*x
        self.record = x
        FtransTmp = np.array([[1, 0, 0, 0],
                            [0, 1, 0, x],
                            [0, 0, 1, self.destance],
                            [0, 0, 0, 1]])
        self.myScene.getTransformByName("变换_股骨约束").matrix = FtransTmp


    #将点放到正确位置
    def getDisByPlane(self,Femur2JGM,Femur3JGM):
        point0 = self.myScene.getMarkupsByName('内侧远端1').getPointsWorld()[0].copy()
        point01 = self.myScene.getMarkupsByName('外侧远端1').getPointsWorld()[0].copy()
        point=(point0+point01)/2
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0].copy()
        

        Femur1JGM = np.array([[30.951, -14.145, 17.976],
                             [-31.236, -1.339, 17.976],
                             [-31.485, -15.010, 17.976]])
        
        d = self.point2area_distance(np.array(Femur1JGM), point)
        self.destance = d - 8
        point1[2]=point1[2]+self.destance
        ras1 = point1
        d = self.point2area_distance(np.array(Femur2JGM), ras1)
        x = d / math.cos(math.radians(6))
        n1=[0,1,0]
        n2 = np.array(ras1) - self.TouYing(Femur2JGM, ras1)
        if np.dot(n1,n2)<0:
            direction = 1
        else:
            direction = -1
        x=direction*x
        points2JGMUp=(Femur2JGM[0]+Femur2JGM[1])/2
        points2JGMUp[2]=points2JGMUp[2]-self.destance
        x=(-self.getDistance(points2JGMUp)/math.cos(math.radians(6))+x)/2
        self.record = x
        FtransTmp = np.array([[1, 0, 0, 0],
                                [0, 1, 0, x],
                                [0, 0, 1, self.destance],
                                [0, 0, 0, 1]])
        
        points2JGMUp=(Femur2JGM[0]+Femur2JGM[1])/2
        points2JGMUp[2]=points2JGMUp[2]-self.destance

        # print('新的z方向距离',-self.getDistance(points2JGMUp))
        # print('jiu的x方向距离',x)


        # 旧方法，对齐后髁点
        # point2 = self.myScene.getMarkupsByName('外侧后髁1').getPointsWorld()[0].copy()
        # point3 = self.myScene.getMarkupsByName('内侧后髁1').getPointsWorld()[0].copy()
        # #对point2及point3进行变换
        # point2+=np.array([0,x,self.destance])
        # point3+=np.array([0,x,self.destance])
        # ang1Point=[point2[0],point2[1],point2[2]]
        # ang2Point=[point2[0],(point3[1]),point2[2]]
        # angle1=self.Angle(ang1Point,ang2Point)
        # print('angle1',angle1)
        # if 1:
        #     angle1+=1
        #     if point2[1]>point3[1]:
        #         angle1=-angle1
        #     #计算绕Z轴旋angle1度的矩阵
        #     martrix=self.GetMarix_z(angle1)
        #     FtransTmp=np.dot(martrix,FtransTmp)
        #     print('FtransTmp',FtransTmp)
        #     FtransTmpInv=np.linalg.inv(FtransTmp)
        #     #更新Femur2JGM及Femur3JGM
        #     for i in range(0,3):
        #         Femur2JGM[i]=np.dot(FtransTmpInv,[Femur2JGM[i][0],Femur2JGM[i][1],Femur2JGM[i][2],1])[0:3]
        #         Femur3JGM[i]=np.dot(FtransTmpInv,[Femur3JGM[i][0],Femur3JGM[i][1],Femur3JGM[i][2],1])[0:3]
        # else:
        #     Femur2JGM=Femur2JGM+np.array([0,-x,-self.destance])
        #     Femur3JGM=Femur3JGM+np.array([0,-x,-self.destance])

        #新的角度计算方法，考虑对齐皮质高点另一侧的的点及皮质高点
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0].copy()
        point1_1 = point1.copy()
        point1_1[0]=point1_1[0]-16
        #计算point1_1在骨骼上的最近点
        pointClose=self.getClosestPoint(point1_1)
        point1+=np.array([0,x,self.destance])
        pointClose+=np.array([0,x,self.destance])
        point1[0]=pointClose[0]
        angel=self.Angle(point1,pointClose)+1
        if (point1[1]>pointClose[1]):
            angel=-angel
        print('angelNew',angel)
        #计算绕Z轴旋angle1度的矩阵
        martrix=self.GetMarix_z(angel)
        FtransTmp=np.dot(martrix,FtransTmp)
        print('FtransTmp',FtransTmp)
        FtransTmpInv=np.linalg.inv(FtransTmp)
        #更新Femur2JGM及Femur3JGM
        for i in range(0,3):
            Femur2JGM[i]=np.dot(FtransTmpInv,[Femur2JGM[i][0],Femur2JGM[i][1],Femur2JGM[i][2],1])[0:3]
            Femur3JGM[i]=np.dot(FtransTmpInv,[Femur3JGM[i][0],Femur3JGM[i][1],Femur3JGM[i][2],1])[0:3]

        #前倾角度计算
        point1 = self.myScene.getMarkupsByName('外侧皮质高点1').getPointsWorld()[0].copy()
        point1[2]=point1[2]+35
        #计算point1在骨骼上的最近点
        pointClose=self.getClosestPoint(point1)
        #在3D slicer中添加一个markups节点，用于显示pointClose
        # PointNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode')
        # PointNode.SetName('pointClose')
        # PointNode.AddControlPoint(pointClose)
        #计算pointClose在平面Femur2JGM上的投影点
        pointClose1=self.getProjectionPoint(pointClose,Femur2JGM)
        normal=pointClose-pointClose1
        normal=normal/np.linalg.norm(normal)
        #判断normal是否与[0,-1,0]同向
        if np.dot(normal,[0,-1,0])<0:
            angel=self.Angle(pointClose1,pointClose)
            print('angel',angel)
            martrix_x=self.GetMarix_x(angel)
            FtransTmp=np.dot(martrix_x,FtransTmp)
            martrix_x_inv=np.linalg.inv(martrix_x)
            for i in range(0,3):
                Femur2JGM[i]=np.dot(martrix_x_inv,[Femur2JGM[i][0],Femur2JGM[i][1],Femur2JGM[i][2],1])[0:3]
                Femur3JGM[i]=np.dot(martrix_x_inv,[Femur3JGM[i][0],Femur3JGM[i][1],Femur3JGM[i][2],1])[0:3]

        else:
            pass

        return Femur2JGM,Femur3JGM,FtransTmp

    #计算点在平面上的投影点，平面由三个点确定
    def getProjectionPoint(self,point,planePoints):
        planeNormal=np.cross(planePoints[1]-planePoints[0],planePoints[2]-planePoints[0])
        planeNormal=planeNormal/np.linalg.norm(planeNormal)
        return point-np.dot(planeNormal,point-planePoints[0])*planeNormal



    #计算点到平面的距离，平面由一个点及法向量确定
    def getPointToPlane(self,point,planePoint,planeNormal):
        return abs(np.dot(planeNormal,point-planePoint))
    # 推荐股骨假体
    def SelectJiaTi(self):
        #self.FirstJieGu()
        #约束条件满足后，两端到骨骼表面的距离。
        #影响条件：
        #1.后髁点到第三刀截骨面距离，与一个标准值 7mm 差越多，得分越低
        #2.覆盖率，后髁边缘离骨骼越远，分越低。前髁边缘离骨骼越远，分越低
        PointPath = self.FilePath+"/假体库/a"
        point2 = self.myScene.getMarkupsByName('外侧后髁1').getPointsWorld()[0].copy()
        point3 = self.myScene.getMarkupsByName('内侧后髁1').getPointsWorld()[0].copy()
        femurUp11=self.myScene.getMarkupsByName('femurUp11').getPointsWorld()[0].copy()
        femurUp21=self.myScene.getMarkupsByName('femurUp21').getPointsWorld()[0].copy()
        femurUpMean=(femurUp11[2]+femurUp21[2])/2

        # 假体型号
        diffList=[]
        FtransList=[]
        list3 = ['1-5', '2', '2-5', '3', '4', '5']
        planePoints=np.array([[ 21.75182915, -31.58379936,  26.24497032],
                        [ 23.03744316, -33.59889984,  30.42037392],
                        [ 23.0080719 , -34.25144196,  33.0945282 ],
                        [ 22.93015862, -34.80111694,  36.79411316],
                        [ 25.76075363, -36.34246063,  37.22349167],
                        [ 25.83369255, -38.84169388,  34.0918045 ]])
        for i in range(0, len(list3)):
            name = 'femur-' + list3[i]
            lujing = os.path.join(PointPath, name + '.txt')
            inputPoints = np.loadtxt(lujing)
            Femur2JGM=inputPoints[0:3]
            Femur3JGM=inputPoints[3:6]
            Femur2JGM1,Femur3JGM1,FtransTmp=self.getDisByPlane(Femur2JGM,Femur3JGM)
            FtransList.append(FtransTmp)
            #d1为假体第三刀最上方的点到对应骨骼指定最高点所在平面的距离
            dd=(Femur3JGM1[0][2]+Femur3JGM1[1][2])/2-(femurUpMean-4)
            if dd>0:
                d1=abs(dd)*3
            else:
                d1=abs(dd)
            #d2及d3为后髁点到第三刀接骨面的距离
            d2=abs(abs(self.point2area_distance(np.array(Femur3JGM1), point3))-7)
            d3=abs(abs(self.point2area_distance(np.array(Femur3JGM1), point2))-7)
            #d4为假体第三刀最上方的点到股骨最近点的距离
            d4=abs(self.getDistance(Femur3JGM1[0].copy()))+abs(self.getDistance(Femur3JGM1[1].copy()))
            #d5为假体后髁点到股骨后髁点的距离
            #对point2及point3进行变换
            point21=np.dot(FtransTmp,[point2[0],point2[1],point2[2],1])[0:3]
            point31=np.dot(FtransTmp,[point3[0],point3[1],point3[2],1])[0:3]
            d5=0#self.getPointToPlane(point21,planePoints[i],np.array([0,1,0]))+self.getPointToPlane(point31,planePoints[i],np.array([0,1,0]))
            #d6为假体第二刀最上方的点到股骨最近点的距离
            d6=abs(self.getDistance(Femur2JGM1[0].copy()))+abs(self.getDistance(Femur2JGM1[1].copy()))
            diffList.append(d1+d2+d3+d4+d5*0.5+d6*2)
            # print('d1:',d1,'d2:',d2,'d3:',d3,'d4:',d4,'d5:',d5,'d6:',d6)

        print(diffList)
        self.minIndex=diffList.index(min(diffList))
        FtransTmp=FtransList[self.minIndex]
        
        self.FemurYueshuMatrix = FtransTmp
        Name = 'femur-' + self.judge + list3[self.minIndex]
        # self.ui.JiaTiName.setText(Name)
        self.jiatiload=Name
        #旋转90
        Ftrans1 = np.array([[1, 0, 0, 0],
            [0, 0, -1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1]])
        newTrans=np.dot(Ftrans1,FtransTmp)
        
        self.HardModel1(newTrans)
        if self.judge == 'L':
            #对targetModel进行X方向的镜像处理
            Ftrans = np.array([[-1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
            transform = vtk.vtkTransform()
            transform.SetMatrix(Ftrans.flatten())
            transform.Update()
            transform_filter = vtk.vtkTransformPolyDataFilter()
            transform_filter.SetInputData(self.polydata)
            transform_filter.SetTransform(transform)
            transform_filter.Update()
            #计算法向量，并反转
            normal = vtk.vtkPolyDataNormals()
            normal.SetInputData(transform_filter.GetOutput())
            normal.FlipNormalsOn()
            normal.Update()
            self.polydata = normal.GetOutput()
            
        #markupsNode=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','P')
        FemurPoints = ['开髓点1', '内侧凹点1', '外侧凸点1', '内侧远端1', '外侧远端1', '内侧后髁1', '外侧后髁1', '外侧皮质高点1', 'A点1', "股骨头球心1"]
        for i in range(len(FemurPoints)):
            PointNode=self.myScene.getMarkupsByName(FemurPoints[i])
            point = PointNode.getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.RemoveAllPoints()
            PointNode.AddPoints(np.dot(newTrans, point)[0:3])
            #markupsNode.AddControlPoint(np.dot(FtransTmp, point)[0:3])
        self.updateLowPoints(newTrans)




    #确定胫骨截骨面，并正确放置假体位置     
    def TibiaJieGu(self):
        # 胫骨截骨面
        TibiaJieGu = self.myScene.AddMarkups('胫骨截骨面')
        TibiaJieGu.AddPoints([30, 0, 0])
        TibiaJieGu.AddPoints([0, 30, 0])
        TibiaJieGu.AddPoints([0, 0, 0])
        point=self.myScene.getMarkupsByName('内侧高点1').getPointsWorld()[0]
        point1=self.myScene.getMarkupsByName('外侧高点1').getPointsWorld()[0]
        point3=self.myScene.getMarkupsByName('胫骨隆凸1').getPointsWorld()[0]
        TibiaJGM = self.myScene.getMarkupsByName('胫骨截骨面').getPointsWorld()
        pointTouYing = np.array(self.TouYing(np.array(TibiaJGM),point))



        xiangliang=(point-pointTouYing)[0:3]
        z=[0,0,1]
        x=np.dot(xiangliang,z)

        print('x',x)
        d = self.point2area_distance(np.array(TibiaJGM), point)
        print('d:',d)
        if x > 0:
            d = -d
        distance = 6 + d

        

        angle_point=(np.array(point)-point1)[0:2]

        angle=self.Angle(angle_point,[1,0])
        
        if(angle>90):
            angle=180-angle
        if(np.dot(angle_point,[0,1])<0):
            angle=-angle
        trans_angle=self.GetMarix_z(angle)
        print("angle:",angle)

        point2 = [(point[0]+point1[0]+point3[0])/3,(point[1]+point1[1])/2,(point[2]+point1[2]+point3[2])/3]


        #a = [point2[0] - point3[0], point2[1] - point3[1], point2[2] - point3[2]]
        TransformTmp =self.myScene.getTransformByName('变换_胫骨约束')
        # if slicer.modules.NoImageWelcomeWidget.judge == 'R':
        #   a[0]=-a[0]
        #   a[1] = -a[1]
        PointPath=self.FilePath+"/假体库/a"
        nameList = ['1-5', '2', '2-5', '3', '4', '5']
        tibiaIndex=[6990, 6847, 5784, 6672, 9178]
        centerList=[]
        diffList=[]
        for i in range(0, len(nameList)):
            inputPoints=[]
            name = 'Tibia-' + nameList[i]
            lujing = os.path.join(PointPath,name+'.txt')
            print('lujing',lujing)
            point  =  np.loadtxt(lujing)
            Ydiff1=point[1][1]-self.getPolyDataPointsByIndex(tibiaIndex[0])[1]
            Ydiff1-=(point[5][1]+point[6][1])/2-(self.getPolyDataPointsByIndex(tibiaIndex[3])[1]+self.getPolyDataPointsByIndex(tibiaIndex[4])[1])/2
            Xdiff1=point[3][0]-self.getPolyDataPointsByIndex(tibiaIndex[2])[0]
            Xdiff1-=point[4][0]-self.getPolyDataPointsByIndex(tibiaIndex[1])[0]
            diffList.append(abs(Ydiff1)+abs(Xdiff1))
            dx=(point[3][0]-self.getPolyDataPointsByIndex(tibiaIndex[2])[0]+(point[4][0]-self.getPolyDataPointsByIndex(tibiaIndex[1])[0]))/2
            dy=point[1][1]-self.getPolyDataPointsByIndex(tibiaIndex[0])[1]
            centerList.append([dx,dy])
        
        #获取最小值的索引
        minIndex=diffList.index(min(diffList))
        self.jiatiload=minIndex
        print(self.jiatiload)
        #获取最小值
        print('distance:',centerList[minIndex])




        TtransTmp = np.array([[1, 0, 0, centerList[minIndex][0]],
                        [0, 1, 0, centerList[minIndex][1]-3],
                        [0, 0, 1, distance],
                        [0, 0, 0, 1]])

        #print('TtransTmp',TtransTmp,'a',a)
        #xzjz = self.GetMarix_z(-2)
        trans = np.dot(TtransTmp,trans_angle)
        TransformTmp.matrix=trans
        Ftransform11 = self.myScene.getTransformByName('变换_胫骨约束').matrix
        Ftrans1 = np.array([[-1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        trans_femur = np.dot(Ftrans1, np.dot(Ftransform11, Ftrans1))
        #旋转90
        Ftrans1 = np.array([[1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, -1, 0, 0],
            [0, 0, 0, 1]])
        newTrans=np.dot(Ftrans1,trans_femur)

        self.HardModel(newTrans)

        self.polydata=self.cropModel(self.polydata, [0, -80, 0], [0, 1, 0])
        trans=np.dot(Ftrans1,Ftransform11)
        # 将所有点复制出一份放到截骨调整中
        pointsList=[]
        TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
        for i in range(len(TibiaPoints)):
            PointNode = self.myScene.getMarkupsByName(TibiaPoints[i] + "1")
            point = self.myScene.getMarkupsByName(TibiaPoints[i] + "1").getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.RemoveAllPoints()
            pnew=np.dot(trans, point)[0:3]*-1
            pointsList.append(list(pnew))
            PointNode.AddPoints(pnew)
        print("pointsList",pointsList)
       
        Ftrans = np.array([[1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        TransformTmp.matrix=Ftrans
        if self.judge == 'L':
            #对targetModel进行X方向的镜像处理
            Ftrans = np.array([[-1, 0, 0, 0],
                [0, 1, 0, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1]])
            transform = vtk.vtkTransform()
            transform.SetMatrix(Ftrans.flatten())
            transform.Update()
            transform_filter = vtk.vtkTransformPolyDataFilter()
            transform_filter.SetInputData(self.polydata)
            transform_filter.SetTransform(transform)
            transform_filter.Update()
            #计算法向量，并反转
            normal = vtk.vtkPolyDataNormals()
            normal.SetInputData(transform_filter.GetOutput())
            normal.FlipNormalsOn()
            normal.Update()
            self.polydata = normal.GetOutput()
        else:
            FemurPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
            for i in range(len(FemurPoints)):
                PointNode=self.myScene.getMarkupsByName(FemurPoints[i] + "1")
                point = PointNode.getPoints()[0]
                point = [point[0], point[1], point[2]]
                PointNode.RemoveAllPoints()
                point[0]=-point[0]
                PointNode.AddPoints(point)


        #self.onJieGuJianXi()
        writer = vtk.vtkSTLWriter()
        writer.SetFileName(self.outPutPath + '/Tibia111.stl')
        writer.SetInputData(self.polydata)
        writer.Write()


    #通过平面对模型进行裁剪
    def cropModel(self,targetModel, planeOrigin, planeNormal):
        # 裁剪
        plane = vtk.vtkPlane()
        plane.SetOrigin(planeOrigin)
        plane.SetNormal(planeNormal)

        planeCollection = vtk.vtkPlaneCollection()
        planeCollection.AddItem(plane)

        clipper = vtk.vtkClipClosedSurface()
        clipper.SetInputData(targetModel)
        clipper.SetClippingPlanes(planeCollection)
        clipper.Update()
        # 输出
        return clipper.GetOutput()



    #推荐胫骨假体
    def SelectTibiaJiaTi(self):
        self.TibiaJieGu()
        # PointPath="static/asset/ssm/假体库/a"
        # list = ['1-5', '2', '2-5', '3', '4', '5']

        # disList=[]
        # diffList=[]
        # for i in range(0, len(list)):
        #     inputPoints=[]
        #     name = 'Tibia-' + list[i]
        #     lujing = os.path.join(PointPath,name+'.txt')
        #     print('lujing',lujing)
        #     point  =  np.loadtxt(lujing)
        #     judge=1
        #     if self.getDistance([0,0,0])>0:
        #         judge=-1
        #     dis1=0
        #     for j in range(3):
        #         dis1=dis1+self.getDistance(point[j])*judge
        #     dis1=dis1/3
        #     diffList.append(dis1)
        #     pointtmp=point.copy()
        #     pointtmp[:,1]=pointtmp[:,1]-dis1

        #     d1=self.getDistance(pointtmp[3])*judge
        #     if d1>0:
        #         d1=d1*1.5
        #     d2=self.getDistance(pointtmp[4])*judge
        #     if d2>0:
        #         d2=d2*1.5
        #     dis2=d1+d2
        #     d1=self.getDistance(pointtmp[5])*judge
        #     if d1>0:
        #         d1=d1*1.5
        #     d2=self.getDistance(pointtmp[6])*judge
        #     if d2>0:
        #         d2=d2*1.5
        #     dis3=d1+d2
            
        #     disEnd=abs(dis2/2)+abs(dis3/2)
        #     disList.append(disEnd)

        # self.jiatiload='Tibia-' + list[disList.index(min(disList))]
        # Ftransform11 = np.array([[1, 0, 0, 0],
        #             [0, 1, 0, diffList[disList.index(min(disList))]],
        #             [0, 0, 1, 0],
        #             [0, 0, 0, 1]])


        # Ftrans1 = np.array([[-1, 0, 0, 0],
        #             [0, -1, 0, 0],
        #             [0, 0, 1, 0],
        #             [0, 0, 0, 1]])
        # trans_femur = np.dot(Ftrans1, np.dot(Ftransform11, Ftrans1))
        # self.HardModel(trans_femur)
        # writer = vtk.vtkSTLWriter()
        # writer.SetFileName("D:/Data/tibiaTest/FemurOut.stl")
        # writer.SetInputData(self.polydata)
        # writer.Write()
        # # 将所有点复制出一份放到截骨调整中
        # TibiaPoints = ['胫骨隆凸', '内侧高点', '外侧高点', '内侧边缘','外侧边缘','胫骨结节','结节上侧边缘','结节内侧边缘', '结节外侧边缘','踝穴中心']
        # for i in range(len(TibiaPoints)):
        #     PointNode = self.myScene.getMarkupsByName(TibiaPoints[i] + "1")
        #     point = PointNode.getPoints()[0]
        #     point = [point[0], point[1], point[2], 1]
        #     PointNode.RemoveAllPoints()
        #     PointNode.AddPoints(np.dot(Ftransform11, point)[0:3])
        # # import numpy as np
        # path='D:/code/python/velyes/static/asset/ssm/假体库/a/Tibia-2.txt'
        # markupsNode=slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode','P')
        # point  =  np.loadtxt(path)
        # for i in range(len(point)):
        #     markupsNode.AddControlPoint(point[i])

    # 对约束进行微调
    def loaddier(self):
        # 第二刀截骨面
 
        Ftransform11 = self.myScene.getTransformByName('变换_股骨约束').matrix
        Ftrans1 = np.array([[-1, 0, 0, 0],
                    [0, -1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        Ftrans2 = np.array([[1, 0, 0, 0],
                    [0, 0, -1, 0],
                    [0, 1, 0, 0],
                    [0, 0, 0, 1]])
        trans_femur = np.dot(Ftrans1, np.dot(Ftransform11, Ftrans1))
        world = np.dot(Ftrans2, Ftransform11)
        self.HardModel(self.FilePath + '/Femur1.stl', trans_femur)

        FemurPoints = ['开髓点', '内侧凹点', '外侧凸点', '内侧远端', '外侧远端', '内侧后髁', '外侧后髁', '外侧皮质高点', 'A点', "股骨头球心",'H点']
        for i in range(len(FemurPoints)):
            PointNode = self.myScene.getMarkupsByName(FemurPoints[i] + "1")
            point = self.myScene.getMarkupsByName(FemurPoints[i]+ "1").getPoints()[0]
            point = [point[0], point[1], point[2], 1]
            PointNode.RemoveAllPoints()
            PointNode.AddPoints(np.dot(world, point)[0:3])

        Ftrans = np.array([[1, 0, 0, 0],
                    [0, 1, 0, 0],
                    [0, 0, 1, 0],
                    [0, 0, 0, 1]])
        self.myScene.getTransformByName('变换_股骨约束').matrix=Ftrans



    def define_area(self, a):
        point1 = a[0]
        point2 = a[1]
        point3 = a[2]
        AB = np.asmatrix(point2 - point1)
        AC = np.asmatrix(point3 - point1)
        N = np.cross(AB, AC)  # 向量叉乘，求法向量
        # Ax+By+Cz
        Ax = N[0, 0]
        By = N[0, 1]
        Cz = N[0, 2]
        D = -(Ax * point1[0] + By * point1[1] + Cz * point1[2])
        return Ax, By, Cz, D

    # 点到面的距离
    def point2area_distance(self, a, point4):
        Ax, By, Cz, D = self.define_area(a)
        mod_d = Ax * point4[0] + By * point4[1] + Cz * point4[2] + D
        mod_area = np.sqrt(np.sum(np.square([Ax, By, Cz])))
        d = abs(mod_d) / mod_area
        return d


    # 获得投影点（a为三个点确定的平面，point为要获得投影点的点）
    def TouYing(self, a, point):
        Ax, By, Cz, D = self.define_area(a)
        k = (Ax * point[0] + By * point[1] + Cz * point[2] + D) / (np.sum(np.square([Ax, By, Cz])))
        b = [point[0] - k * Ax, point[1] - k * By, point[2] - k * Cz]
        return b

    # 求角度-传递两个向量（求两个向量的夹角）
    def Angle(self, xiangliang1, xiangliang2):
        import math
        cosa = np.dot(xiangliang1, xiangliang2)/math.sqrt(np.dot(xiangliang1,xiangliang1))/math.sqrt(np.dot(xiangliang2, xiangliang2))
        a = math.degrees(math.acos(cosa))
        return a
    #旋转角度变换
    def GetMarix(self,trans,jd,point):
        import math
        jd = math.radians(jd)
        trans_ni=np.linalg.inv(trans)
        Tjxlx=[1,0,0]
        xzjz = [[math.cos(jd) + Tjxlx[0] * Tjxlx[0] * (1 - math.cos(jd)),
                    -Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[1] * Tjxlx[1] * (1 - math.cos(jd)),
                    -Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [-Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)),
                    Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[2] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [0, 0, 0, 1]]
        
        point=np.array([point[0],point[1],point[2],1])
        point_tmp1=np.dot(trans_ni,point)
        point_tmp2=np.dot(xzjz,point_tmp1)
        point=np.dot(trans,point_tmp2)
        return point[0:3]

    def GetMarix_z(self,jd):
        import math
        jd = math.radians(jd)
        Tjxlx=[0,0,1]
        xzjz = np.array([[math.cos(jd) + Tjxlx[0] * Tjxlx[0] * (1 - math.cos(jd)),
                    -Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[1] * Tjxlx[1] * (1 - math.cos(jd)),
                    -Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [-Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)),
                    Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)),
                    math.cos(jd) + Tjxlx[2] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                [0, 0, 0, 1]])
        return xzjz

    def GetMarix_x(self,jd):
            jd = math.radians(jd)
            Tjxlx=[1,0,0]
            xzjz = np.array([[math.cos(jd) + Tjxlx[0] * Tjxlx[0] * (1 - math.cos(jd)),
                        -Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                        Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                    [Tjxlx[2] * math.sin(jd) + Tjxlx[0] * Tjxlx[1] * (1 - math.cos(jd)),
                        math.cos(jd) + Tjxlx[1] * Tjxlx[1] * (1 - math.cos(jd)),
                        -Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                    [-Tjxlx[1] * math.sin(jd) + Tjxlx[0] * Tjxlx[2] * (1 - math.cos(jd)),
                        Tjxlx[0] * math.sin(jd) + Tjxlx[1] * Tjxlx[2] * (1 - math.cos(jd)),
                        math.cos(jd) + Tjxlx[2] * Tjxlx[2] * (1 - math.cos(jd)), 0],
                    [0, 0, 0, 1]])
            return xzjz
    