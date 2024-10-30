import logging
import math
import os
from typing import Annotated, Optional

import numpy as np
import qt
import slicer.util
import vtk
import time
import slicer
from slicer.i18n import tr as _
from slicer.i18n import translate
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin


#
# Surgical_Navigation 
#


class Surgical_Navigation(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = _("Surgical_Navigation")  # TODO: make this more human readable by adding spaces
        # TODO: set categories (folders where the module shows up in the module selector)
        self.parent.categories = [translate("qSlicerAbstractCoreModule", "Examples")]
        self.parent.dependencies = []  # TODO: add here list of module names that this module requires
        self.parent.contributors = ["John Doe (AnyWare Corp.)"]  # TODO: replace with "Firstname Lastname (Organization)"
        # TODO: update with short description of the module and a link to online module documentation
        # _() function marks text as translatable to other languages
        self.parent.helpText = _("""
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#Surgical_Navigation">module documentation</a>.
""")

#
# Surgical_NavigationWidget
#
class Surgical_NavigationWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
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

        self.threeDViews = [] #用于存储两个3d视图的实例

        self.lineactor_left = rendereractor()
        self.lineactor_right = rendereractor()

        self.state = 1 #三种绘制3D 窗口中线的状态0，1，2
        self.last_angle = None
        self.last_minZInner = 0
        self.last_minZOuter = 0
        self.is_pause = False
        # 绘制完成时间
        self.draw_time = 0

        self.point_left_dict = {
            'point_presetline3d1': [0, 0, 0],
            'point_presetline3d2': [100, 100, 100],
            'point_realline3d1': [0, 0, 0],
            'point_realline3d2': [100, 100, 100],
            'point_downarrowpoint3d1': [50, 50, 50],
            'point_uparrowpoint3d2': [100, 100, 100]
        }

        self.point_right_dict = {
            'point_presetline3d1': [0, 0, 0],
            'point_presetline3d2': [100, 100, 100],
            'point_realline3d1': [0, 0, 0],
            'point_realline3d2': [100, 100, 100],
            'point_downarrowpoint3d1': [50, 50, 50],
            'point_downarrowpoint3d2': [75, 75, 75],
            'point_dashline3d1': [100, 100, 100],
            'point_dashline3d2': [200, 200, 200],
            'point_brokenline3d1': [300, 300, 300],
            'point_brokenline3d2': [200, 200, 200],
        }

    def setup(self) -> None:
        """Called when the user opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer).
        # Additional widgets can be instantiated manually and added to self.layout.
        uiWidget = slicer.util.loadUI(self.resourcePath("UI/Surgical_Navigation.ui"))
        self.layout.addWidget(uiWidget)
        self.ui = slicer.util.childWidgetVariables(uiWidget)

        # Set scene in MRML widgets. Make sure that in Qt designer the top-level qMRMLWidget's
        # "mrmlSceneChanged(vtkMRMLScene*)" signal in is connected to each MRML widget's.
        # "setMRMLScene(vtkMRMLScene*)" slot.
        uiWidget.setMRMLScene(slicer.mrmlScene)

        # Create logic class. Logic implements all computations that should be possible to run
        # in batch mode, without a graphical user interface.
        self.logic = Surgical_NavigationLogic()

        

        self.femurTransBaseTibiaNode=None
        self.setUpAll3DView()

        #self.draw_line_actor(self.point_left_dict, self.point_right_dict)

        # Connections
    def enter(self) -> None:
        """
        每次用户打开该模块时调用，
        功能是初始化参数节点并确保其被观察。
        """
        self.onEnterNavigation()
        self.getLinePoints(0)
        
    def set_state(self, state):
        self.state = state

    def setUpAll3DView(self):
        """
        设置所有 3D 视图。

        该方法创建并配置多个 3D 视图节点，并将它们与 UI 中的 3D 视图小部件相关联。

        参数:
        无

        返回:
        无
        """

        self.widget_Top = CustomWindow()

        self.ui.widget_4.layout().addWidget(self.widget_Top)
        # 为widget_bottom设置布局
        self.widget_Top.setLayout(qt.QHBoxLayout())
        self.rendererList = []



        

        # 设置layout边缘间距
        self.widget_Top.layout().setContentsMargins(0, 0, 0, 0)

        for i in range(2):
            # 创建 MRML 视图节点
            viewOwnerNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScriptedModuleNode")
            viewLogic = slicer.vtkMRMLViewLogic()
            viewLogic.SetMRMLScene(slicer.mrmlScene)
            viewNode = viewLogic.AddViewNode(f"Guild3DView_{i}")  # 为每个视图节点提供唯一名称
            viewNode.SetLayoutLabel(f"Guild{i}")  # 为每个视图节点设置标签
            viewNode.SetLayoutColor(0, 0, 0)
            viewNode.SetBackgroundColor(0, 0, 0)
            viewNode.SetAndObserveParentLayoutNodeID(viewOwnerNode.GetID())
            # 创建 3D 视图小部件
            threeDViewWidget = slicer.qMRMLThreeDWidget()
            
            threeDViewWidget.setMRMLScene(slicer.mrmlScene)
            threeDViewWidget.setMRMLViewNode(viewNode)
            threeDViewWidget.show()
            if i<3:
                self.widget_Top.layout().addWidget(threeDViewWidget)

            self.threeDViews.append(threeDViewWidget)
            renderWindow = threeDViewWidget.threeDView().renderWindow()
            # 在添加渲染器之前，必须先设置 renderWindow 的层数
            renderWindow.SetNumberOfLayers(3)  # 确保至少有 3 层，层编号从 0 开始
            renderer = renderWindow.GetRenderers().GetFirstRenderer()
            for i in range(2):
                newRenderer = vtk.vtkRenderer()
                newRenderer.SetActiveCamera(renderer.GetActiveCamera())
                newRenderer.SetLayer(i+1)
                renderWindow.AddRenderer(newRenderer)
                self.rendererList.append(newRenderer)

            renderWindow.Render()


        for i in range(2):
            self.threeDViews[i].threeDView().scheduleRender()

        # 设置Verifylabel位置
        self.verifyLabel = VerifyLabel(self.widget_Top)
        self.verifyLabel.setGeometry(self.widget_Top.width / 2 - 50, self.widget_Top.height / 2 - 50, 100, 100)

            
        self.viewButtonList=[]
        View1TopButton = ViewPopWidget1(1)
        View1TopButton.setParent(self.threeDViews[0])
        View1TopButton.setPositionByWidget(self.threeDViews[0],'top')
        View1TopButton.show()
        self.viewButtonList.append(View1TopButton)

        View1BottomButton = ViewPopWidget1(3)
        View1BottomButton.setParent(self.threeDViews[0])
        View1BottomButton.setPositionByWidget(self.threeDViews[0],'bottom')
        View1BottomButton.show()
        self.viewButtonList.append(View1BottomButton)


        View2TopButton = ViewPopWidget1(4)
        View2TopButton.setParent(self.threeDViews[1])
        View2TopButton.setPositionByWidget(self.threeDViews[1],'top')
        View2TopButton.show()
        self.viewButtonList.append(View2TopButton)
        #View2TopButton.CenterButton.clicked.connect(self.testbutton)

        View2BottomButton = ViewPopWidget1(2)
        View2BottomButton.setParent(self.threeDViews[1])
        View2BottomButton.setPositionByWidget(self.threeDViews[1],'bottom_left')
        View2BottomButton.show()
        self.viewButtonList.append(View2BottomButton)
        #View2BottomButton.CenterButton.clicked.connect(self.testbutton2)


        View2BottomButton_1 = ViewPopWidget1(2)
        View2BottomButton_1.setParent(self.threeDViews[1])
        View2BottomButton_1.setPositionByWidget(self.threeDViews[1],'bottom_right')
        View2BottomButton_1.show()
        self.viewButtonList.append(View2BottomButton_1)
        self.onSetUpCameraPostion()


    # 10.17 
    # 设置相机位置
    def onSetUpCameraPostion(self):
        # 设置相机位置
        cameraNode3 = self.threeDViews[0].viewWidget().cameraNode()
        cameraNode3.SetPosition(495.7681850602074, 32.428406098246406, 56.234377)
        cameraNode3.SetFocalPoint(0, 0, 0)
        cameraNode3.SetViewUp(0,0,1)

        cameraNode1 = self.threeDViews[1].viewWidget().cameraNode()
        cameraNode1.SetPosition(0,500,0)
        cameraNode1.SetFocalPoint(0, 0, 0)
        cameraNode1.SetViewUp(0,0,1)

    def rotation_matrix_to_euler_angles(self,matrix):
        # 提取旋转部分
        R = matrix[:3, :3]
        
        # 计算欧拉角
        sy = math.sqrt(R[0, 0] ** 2 + R[1, 0] ** 2)  # 计算sy，避免奇异情况

        singular = sy < 1e-6  # 判断是否为奇异情况
        if not singular:
            x = math.atan2(R[2, 1], R[2, 2])  # 绕X轴的旋转
            y = math.atan2(-R[2, 0], sy)      # 绕Y轴的旋转
            z = math.atan2(R[1, 0], R[0, 0])  # 绕Z轴的旋转
        else:
            x = math.atan2(-R[1, 2], R[1, 1])  # 特殊处理
            y = math.atan2(-R[2, 0], sy)
            z = 0

        return np.array([x, y, z])

    def euler_angles_to_rotation_matrix(self,angles):
        # 提取欧拉角
        x, y, z = angles
        
        # 计算旋转矩阵
        Rx = np.array([[1, 0, 0],
                    [0, np.cos(x), -np.sin(x)],
                    [0, np.sin(x), np.cos(x)]])
        
        Ry = np.array([[np.cos(y), 0, np.sin(y)],
                    [0, 1, 0],
                    [-np.sin(y), 0, np.cos(y)]])
        
        Rz = np.array([[np.cos(z), -np.sin(z), 0],
                    [np.sin(z), np.cos(z), 0],
                    [0, 0, 1]])
        
        return Rz @ Ry @ Rx

    def caculateFirstTransform(self,matrix):
        # 转欧拉角
        # 获取旋转矩阵
        R = matrix[:3, :3]
        # 计算欧拉角
        angles = self.rotation_matrix_to_euler_angles(R)
        angles[2] = 0
        # 计算新的旋转矩阵
        R = self.euler_angles_to_rotation_matrix(angles)
        # 创建变换矩阵
        constrained_matrix = np.eye(4)
        constrained_matrix[:3, :3] = R
        constrained_matrix[2, 3] = matrix[2, 3]
        return constrained_matrix

    def caculateSecondTransform(self,matrix):
        # 转欧拉角
        # 获取旋转矩阵
        R = matrix[:3, :3]
        # 计算欧拉角
        angles = self.rotation_matrix_to_euler_angles(R)
        angles[0] = 0
        angles[1] = 0
        # 计算新的旋转矩阵
        R = self.euler_angles_to_rotation_matrix(angles)
        # 创建变换矩阵
        constrained_matrix = np.eye(4)
        constrained_matrix[:3, :3] = R
        constrained_matrix[1, 3] = matrix[1, 3]
        return constrained_matrix

    def caculateFemurFirstTransform(self,caller=None,event=None):
        # 获取截骨板相对于当前在原点处的股骨的变换
        FemurTransNode=slicer.util.getNode('Femurtool_Transform')
        femurTrans=slicer.util.arrayFromTransformMatrix(FemurTransNode)
        FemurToOriginTrans=np.dot(np.linalg.inv(self.FemurToRealTrans),np.linalg.inv(femurTrans))

        FemurCutNode=slicer.util.getNode('FemurCutNode')
        FemurCutTrans=slicer.util.arrayFromTransformMatrix(FemurCutNode)
        FemurCutTransReal=np.dot(FemurToOriginTrans,FemurCutTrans)
        # 再按一定规则获取变换
        FemurCutTransRealToBone=self.caculateFirstTransform(FemurCutTransReal)
        # 再变换至当前相对于胫骨的位置
        femurTransBaseTibiaNode=slicer.util.getNode('FemurTransBaseTibia')
        femurTransBaseTibia=slicer.util.arrayFromTransformMatrix(femurTransBaseTibiaNode)
        FemurCutTransRealToBone=np.dot(femurTransBaseTibia,FemurCutTransRealToBone)



        femurJtTransNode=slicer.util.getNode('FemurJTTransNode')
        femurJtTransNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(FemurCutTransRealToBone))
        self.getLinePoints(1)
        self.caculateFemurInfFirst()
        return FemurCutTransRealToBone


    def caculateFemurSecondTransform(self,caller=None,event=None):
        # 获取截骨板相对于当前在原点处的股骨的变换
        FemurTransNode=slicer.util.getNode('Femurtool_Transform')
        femurTrans=slicer.util.arrayFromTransformMatrix(FemurTransNode)
        FemurToOriginTrans=np.dot(np.linalg.inv(self.FemurToRealTrans),np.linalg.inv(femurTrans))

        FemurCutNode=slicer.util.getNode('FemurCutNode')
        FemurCutTrans=slicer.util.arrayFromTransformMatrix(FemurCutNode)
        FemurCutTransReal=np.dot(FemurToOriginTrans,FemurCutTrans)
        # 再按一定规则获取变换
        FemurCutTransRealToBone=self.caculateSecondTransform(FemurCutTransReal)
        # 再变换至当前相对于胫骨的位置
        femurTransBaseTibiaNode=slicer.util.getNode('FemurTransBaseTibia')
        femurTransBaseTibia=slicer.util.arrayFromTransformMatrix(femurTransBaseTibiaNode)
        FemurCutTransRealToBone=np.dot(femurTransBaseTibia,FemurCutTransRealToBone)
        femurJtTransNode=slicer.util.getNode('FemurJTTransNode')
        femurJtTransNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(FemurCutTransRealToBone))
        self.getLinePoints(2)
        self.caculateFemurInfSecond()
        return FemurCutTransRealToBone
        

    def caculateTibiaFirstTransform(self,caller=None,event=None):
        TibiaTransNode=slicer.util.getNode('Tibiatool_Transform')
        tibiaTrans=slicer.util.arrayFromTransformMatrix(TibiaTransNode)
        TibiaToOriginTrans=np.dot(np.linalg.inv(self.TibiaToRealTrans),np.linalg.inv(tibiaTrans))

        TibiaCutNode=slicer.util.getNode('djpoint_Transform')
        TibiaCutTrans=slicer.util.arrayFromTransformMatrix(TibiaCutNode)
        cutTransBaseCutTool=np.array([[-1.19445301e-02,  9.98103135e-01, -6.03942033e-02,
                                        -4.80000000e+01],
                                    [ 9.13325457e-02, -5.90570269e-02, -9.94067721e-01,
                                        -1.00000000e+00],
                                    [-9.95748811e-01, -1.73896282e-02, -9.04538918e-02,
                                        0.00000000e+00],
                                    [ 0.00000000e+00,  0.00000000e+00,  0.00000000e+00,
                                        1.00000000e+00]])
        TibiaCutTrans=np.dot(TibiaCutTrans,cutTransBaseCutTool)
        TibiaCutTransReal=np.dot(TibiaToOriginTrans,TibiaCutTrans)
        TibiaCutTransReal_Translation=TibiaCutTransReal[0:3,3]
        # 如果截骨版距离胫骨小于200mm，则认为截骨板已经到位，开启计算
        length=np.linalg.norm(TibiaCutTransReal_Translation)
        if length<200:
            tibiaJtTransNode=slicer.util.getNode('TibiaJTTransNode')
            tibiaJtTransNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(self.caculateFirstTransform(TibiaCutTransReal)))
            self.getLinePoints(0)
            self.caculateTibiaInf()



    def caculateTibiaInf(self, caller=None, event=None):
        if not self.is_pause:
            return
        inf = slicer.modules.kneeplane.widgetRepresentation().self().onCalculate()
        indices = [9, 10, 7, 8]
        buttons = [0, 2, 3, 4]
        self._updateButtons(inf, indices, buttons)
    
    def caculateFemurInfFirst(self, caller=None, event=None):
        if not self.is_pause:
            return
        inf = slicer.modules.kneeplane.widgetRepresentation().self().onCalculate()
        indices = [5, 6, 0, 1]
        buttons = [0, 2, 3, 4]
        self._updateButtons(inf, indices, buttons)
    
    def caculateFemurInfSecond(self, caller=None, event=None):
        if not self.is_pause:
            return
        inf = slicer.modules.kneeplane.widgetRepresentation().self().onCalculate()
        indices = [5, 4, 6, 2, 3]
        buttons = [0, 1, 2, 3, 4]
        self._updateButtons(inf, indices, buttons)
    
    def _updateButtons(self, inf, indices, buttons):
        for button_index, inf_index in zip(buttons, indices):
            self.viewButtonList[button_index].CenterButton.setCenterNumber(int(inf[inf_index]))
            if abs(self.planeInfo[inf_index] - inf[inf_index]) < 0.55:
                self.viewButtonList[button_index].CenterButton.setTextColor('blue')
            else:
                self.viewButtonList[button_index].CenterButton.setTextColor('white')



    



    # 进入导航模式
    def onEnterNavigation(self):


        self.qMRML_widget = slicer.modules.kneeplane.widgetRepresentation().self().qMRML_widget
        if self.qMRML_widget is not None:
            self.ui.widget_4.layout().addWidget(self.qMRML_widget)


            # 设置layout比例为2:1
            self.ui.widget_4.layout().setStretchFactor(self.widget_Top, 2)
            self.ui.widget_4.layout().setStretchFactor(self.qMRML_widget, 1)

        if (self.femurTransBaseTibiaNode==None):
            self.FemurModel=slicer.util.getNode('FemurModel')
            self.TibiaModel=slicer.util.getNode('TibiaModel')
            # 设置为以骨骼为根坐标系
            # 计算股骨工具相对于胫骨工具的变换，用于计算股骨的变换
            
            self.femurTransBaseTibiaNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode")
            self.femurTransBaseTibiaNode.SetName("FemurTransBaseTibia")
            FemurTransNode=slicer.util.getNode('Femurtool_Transform')

            # 添加观察者
            FemurTransNode.AddObserver(self.femurTransBaseTibiaNode.TransformModifiedEvent, self.onChangeFemurTransBaseTibia)

            # 创建规划的线
            self.initLineNode(0)
            self.getFemurAndTibiaToRealTransform()

            # 临时测试使用，之后删除
            # 创建一个transformNode
            FemurCutNode=slicer.util.getNode('djpoint_Transform')
            # 添加观察者
            FemurCutNode.AddObserver(FemurCutNode.TransformModifiedEvent, self.caculateTibiaFirstTransform)
            tibiaPointNode=slicer.util.getNode('胫骨隆凸')
            tibiaPoint=tibiaPointNode.GetNthControlPointPositionWorld(0)
            # 创建一个4*4单位矩阵
            matrix=np.eye(4)
            # 将点设置在矩阵的第三列
            matrix[0:3,3]=tibiaPoint
            # 设置变换
            FemurCutNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(matrix))
            FemurCutNode.CreateDefaultDisplayNodes()
            FemurCutNode.GetDisplayNode().SetEditorVisibility(1)

            # 创建一个transformNode
            FemurCutNode=slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode")
            FemurCutNode.SetName("FemurCutNode")
            # 添加观察者
            FemurCutNode.AddObserver(FemurCutNode.TransformModifiedEvent, self.caculateFemurSecondTransform)
            femurPointNode=slicer.util.getNode('开髓点')
            femurPoint=femurPointNode.GetNthControlPointPositionWorld(0)
            # 创建一个4*4单位矩阵
            matrix=np.eye(4)
            # 将点设置在矩阵的第三列
            matrix[0:3,3]=femurPoint
            # 设置变换
            FemurCutNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(matrix))
            FemurCutNode.CreateDefaultDisplayNodes()
            FemurCutNode.GetDisplayNode().SetEditorVisibility(1)

        # 获取此时股骨及胫骨的假体截骨参数
        self.planeInfo = slicer.modules.kneeplane.widgetRepresentation().self().onCalculate()



        # 将股骨设置在self.femurTransBaseTibiaNode下
        self.FemurModel.SetAndObserveTransformNodeID(self.femurTransBaseTibiaNode.GetID())

        self.FemurModel.GetDisplayNode().SetVisibility(1)
        self.TibiaModel.GetDisplayNode().SetVisibility(1)
        # 将股骨的标志点设置在self.femurTransBaseTibiaNode下
        femurMarkupsNode=slicer.util.getNode('FemurPoints')
        femurMarkupsNode.SetAndObserveTransformNodeID(self.femurTransBaseTibiaNode.GetID())
        LowestPointsInner=slicer.util.getNode('LowestPointsInner')
        LowestPointsInner.SetAndObserveTransformNodeID(self.femurTransBaseTibiaNode.GetID())
        LowestPointsOuter=slicer.util.getNode('LowestPointsOuter')
        LowestPointsOuter.SetAndObserveTransformNodeID(self.femurTransBaseTibiaNode.GetID())


        # 计算股骨假体相对于股骨的变换
        self.femurJtTransBaseFemur=slicer.util.arrayFromTransformMatrix(slicer.util.getNode('FemurTransNode'))
        self.femurJtTransBaseFemur=np.linalg.inv(self.femurJtTransBaseFemur)
        # 将其赋值给股骨假体的变换
        FemurJTTransNode=slicer.util.getNode('FemurJTTransNode')
        FemurJTTransNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(self.femurJtTransBaseFemur))
        FemurJTTransNode.SetAndObserveTransformNodeID(self.femurTransBaseTibiaNode.GetID())
        
        # 更新绘制规划的线
        self.initLineNode(1)



    def onEnterPlanning(self):

        self.qMRML_widget = slicer.modules.surgical_navigation.widgetRepresentation().self().qMRML_widget
        if self.qMRML_widget is not None:
            slicer.modules.kneeplane.widgetRepresentation().self().ui.painter_Curve_widget.layout().addWidget(self.qMRML_widget)
            

        # 将股骨设置在FemurTransNode下
        self.FemurModel.SetAndObserveTransformNodeID(slicer.util.getNode('FemurTransNode').GetID())
        self.FemurModel.GetDisplayNode().SetVisibility(0)
        self.TibiaModel.GetDisplayNode().SetVisibility(0)
        # 将股骨的标志点设置在FemurTransNode下
        femurMarkupsNode=slicer.util.getNode('FemurPoints')
        femurMarkupsNode.SetAndObserveTransformNodeID(slicer.util.getNode('FemurTransNode').GetID())
        LowestPointsInner=slicer.util.getNode('LowestPointsInner')
        LowestPointsInner.SetAndObserveTransformNodeID(slicer.util.getNode('FemurTransNode').GetID())
        LowestPointsOuter=slicer.util.getNode('LowestPointsOuter')
        LowestPointsOuter.SetAndObserveTransformNodeID(slicer.util.getNode('FemurTransNode').GetID())


        # 将股骨假体变换设置为单位矩阵
        FemurJTTransNode=slicer.util.getNode('FemurJTTransNode')
        FemurJTTransNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(np.eye(4)))
        # 将FemurJTTransNode父级设置为空
        FemurJTTransNode.SetAndObserveTransformNodeID(None)

        # 将胫骨假体变换设置为单位矩阵
        TibiaJTTransNode=slicer.util.getNode('TibiaJTTransNode')
        TibiaJTTransNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(np.eye(4)))
        # 将TibiaJTTransNode父级设置为空
        TibiaJTTransNode.SetAndObserveTransformNodeID(None)


    # 获取股骨和胫骨到真实位置的变换
    def getFemurAndTibiaToRealTransform(self):
        FemurFromPoints=slicer.util.arrayFromMarkupsControlPoints(slicer.util.getNode('FemurPoints'))[0:6]
        TibiaFromPoints=slicer.util.arrayFromMarkupsControlPoints(slicer.util.getNode('TibiaPoints'))[0:6]
        FemurToPointsName= ['开髓点', '内侧凹点', '外侧凸点', '内侧远端区域', '外侧远端区域', '内侧后髁区域', '外侧后髁区域', '外侧皮质高点', 'A点', 'H点']
        FemurToPoints=[]
        for i in range(6):
            FemurToPoints.append(slicer.util.getNode(FemurToPointsName[i]).GetNthControlPointPosition(0))
        TibiaToPoints=[]
        TibiaToPointsName=['胫骨隆凸', '胫骨内侧区域', '胫骨外侧区域', '内侧边缘','外侧边缘','胫骨结节区域','结节上侧边缘','结节内侧边缘', '结节外侧边缘','内踝点','外踝点']
        for i in range(6):
            TibiaToPoints.append(slicer.util.getNode(TibiaToPointsName[i]).GetNthControlPointPosition(0))
        self.FemurToRealTrans=self.registion(FemurFromPoints,FemurToPoints)
        self.TibiaToRealTrans=self.registion(TibiaFromPoints,TibiaToPoints)





    def create_line_node(self,name, visibility, parent_node_id):
        line_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode")
        line_node.SetName(name)
        line_node.GetDisplayNode().SetVisibility(visibility)
        line_node.SetAndObserveTransformNodeID(parent_node_id)
        return line_node

    def setLinePoints(self,node1,node2,point1,point2):
        node1.RemoveAllControlPoints()
        node2.RemoveAllControlPoints()
        node1.AddControlPoint(point1)
        node1.AddControlPoint(point2)
        node2.AddControlPoint(point1)
        node2.AddControlPoint(point2)


    # 初始化或者更新用于绘制线的节点
    def initLineNode(self,times):
        if times==0:
            # 胫骨截骨线
            self.tibiaCutSideLineNode = self.create_line_node("TibiaCutSideLine", 0, None)
            self.tibiaCutFrontLineNode = self.create_line_node("TibiaCutFrontLine", 0, None)
            self.tibiaRealTimeCutSideLineNode = self.create_line_node("TibiaRealTimeCutSideLine", 0, slicer.util.getNode('TibiaJTTransNode').GetID())
            self.tibiaRealTimeCutFrontLineNode = self.create_line_node("TibiaRealTimeCutFrontLine", 0, slicer.util.getNode('TibiaJTTransNode').GetID())

            # 股骨第一截骨线
            self.femurFirstCutSideLineNode = self.create_line_node("FemurFirstCutSideLine", 0, self.femurTransBaseTibiaNode.GetID())
            self.femurFirstCutFrontLineNode = self.create_line_node("FemurFirstCutFrontLine", 0, self.femurTransBaseTibiaNode.GetID())
            self.femurRealTimeFirstCutSideLineNode = self.create_line_node("FemurRealTimeFirstCutSideLine", 0, slicer.util.getNode('FemurJTTransNode').GetID())
            self.femurRealTimeFirstCutFrontLineNode = self.create_line_node("FemurRealTimeFirstCutFrontLine", 0, slicer.util.getNode('FemurJTTransNode').GetID())

            # 股骨第二截骨线
            self.femurSecondCutSideLineNode = self.create_line_node("FemurSecondCutSideLine", 0, self.femurTransBaseTibiaNode.GetID())
            self.femurSecondCutFrontLineNode = self.create_line_node("FemurSecondCutFrontLine", 0, self.femurTransBaseTibiaNode.GetID())
            self.femurRealTimeSecondCutSideLineNode = self.create_line_node("FemurRealTimeSecondCutSideLine", 0, slicer.util.getNode('FemurJTTransNode').GetID())
            self.femurRealTimeSecondCutFrontLineNode = self.create_line_node("FemurRealTimeSecondCutFrontLine", 0, slicer.util.getNode('FemurJTTransNode').GetID())

            # 股骨第三截骨线
            self.femurThirdCutSideLineNode = self.create_line_node("FemurThirdCutSideLine", 0, self.femurTransBaseTibiaNode.GetID())
            self.femurThirdCutFrontLineNode = self.create_line_node("FemurThirdCutFrontLine", 0, self.femurTransBaseTibiaNode.GetID())
            self.femurRealTimeThirdCutSideLineNode = self.create_line_node("FemurRealTimeThirdCutSideLine", 0, slicer.util.getNode('FemurJTTransNode').GetID())
            self.femurRealTimeThirdCutFrontLineNode = self.create_line_node("FemurRealTimeThirdCutFrontLine", 0, slicer.util.getNode('FemurJTTransNode').GetID())

        #更新节点的位置
        # 胫骨截骨线
        point1=self.project_point_to_plane([0,-40,0],'TibiaPlane')
        point2=self.project_point_to_plane([0,40,0],'TibiaPlane')
        self.setLinePoints(self.tibiaCutSideLineNode,self.tibiaRealTimeCutSideLineNode,point1,point2)
        point1=self.project_point_to_plane([-40,0,0],'TibiaPlane')
        point2=self.project_point_to_plane([40,0,0],'TibiaPlane')
        self.setLinePoints(self.tibiaCutFrontLineNode,self.tibiaRealTimeCutFrontLineNode,point1,point2)

        # 股骨第一截骨线
        point1=self.project_point_to_plane([0,-40,0],'FemurPlane0')
        point2=self.project_point_to_plane([0,40,0],'FemurPlane0')
        self.setLinePoints(self.femurFirstCutSideLineNode,self.femurRealTimeFirstCutSideLineNode,point1,point2)
        point1=self.project_point_to_plane([-40,0,0],'FemurPlane0')
        point2=self.project_point_to_plane([40,0,0],'FemurPlane0')
        self.setLinePoints(self.femurFirstCutFrontLineNode,self.femurRealTimeFirstCutFrontLineNode,point1,point2)

        # 股骨第二截骨线
        point1=self.project_point_to_plane([0,0,10],'FemurPlane1')
        point2=self.project_point_to_plane([0,0,70],'FemurPlane1')
        self.setLinePoints(self.femurSecondCutSideLineNode,self.femurRealTimeSecondCutSideLineNode,point1,point2)
        point1=self.project_point_to_plane([-40,0,0],'FemurPlane1')
        point2=self.project_point_to_plane([40,0,0],'FemurPlane1')
        self.setLinePoints(self.femurSecondCutFrontLineNode,self.femurRealTimeSecondCutFrontLineNode,point1,point2)

        # 股骨第三截骨线
        point1=self.project_point_to_plane([-25,0,0],'FemurPlane2')
        point2=self.project_point_to_plane([25,0,0],'FemurPlane2')
        self.setLinePoints(self.femurThirdCutFrontLineNode,self.femurRealTimeThirdCutFrontLineNode,point1,point2)


    def getLinePoints(self,type):
        if type==0:
            
            # 胫骨第一截骨线
            self.state = 1
            SideLinePoint1=self.tibiaCutSideLineNode.GetNthControlPointPositionWorld(0)
            SideLinePoint2=self.tibiaCutSideLineNode.GetNthControlPointPositionWorld(1)
            FrontLinePoint1=self.tibiaCutFrontLineNode.GetNthControlPointPositionWorld(0)
            FrontLinePoint2=self.tibiaCutFrontLineNode.GetNthControlPointPositionWorld(1)
            RealTimeSideLinePoint1=self.tibiaRealTimeCutSideLineNode.GetNthControlPointPositionWorld(0)
            RealTimeSideLinePoint2=self.tibiaRealTimeCutSideLineNode.GetNthControlPointPositionWorld(1)
            RealTimeFrontLinePoint1=self.tibiaRealTimeCutFrontLineNode.GetNthControlPointPositionWorld(0)
            RealTimeFrontLinePoint2=self.tibiaRealTimeCutFrontLineNode.GetNthControlPointPositionWorld(1)
            arrayPoint1=slicer.util.getNode('TibiaPoints').GetNthControlPointPositionWorld(1)
            arrayPoint2=slicer.util.getNode('TibiaPoints').GetNthControlPointPositionWorld(2)
            self.point_left_dict['point_presetline3d1'] = SideLinePoint1
            self.point_left_dict['point_presetline3d2'] = SideLinePoint2
            self.point_left_dict['point_realline3d1'] = RealTimeSideLinePoint1
            self.point_left_dict['point_realline3d2'] = RealTimeSideLinePoint2

            self.point_right_dict['point_presetline3d1'] = FrontLinePoint1
            self.point_right_dict['point_presetline3d2'] = FrontLinePoint2
            self.point_right_dict['point_realline3d1'] = RealTimeFrontLinePoint1
            self.point_right_dict['point_realline3d2'] = RealTimeFrontLinePoint2

            self.point_right_dict['point_downarrowpoint3d1'] = arrayPoint1
            self.point_right_dict['point_downarrowpoint3d2'] = arrayPoint2

            self.draw_line_actor(self.point_left_dict, self.point_right_dict)

            # 更新renderWindow
            self.threeDViews[0].threeDView().renderWindow().Render()
            self.threeDViews[1].threeDView().renderWindow().Render()

        elif type==1:

            # 股骨第一截骨线
            self.state = 2
            FirstSideLinePoint1=self.femurFirstCutSideLineNode.GetNthControlPointPositionWorld(0)
            FirstSideLinePoint2=self.femurFirstCutSideLineNode.GetNthControlPointPositionWorld(1)
            FirstFrontLinePoint1=self.femurFirstCutFrontLineNode.GetNthControlPointPositionWorld(0)
            FirstFrontLinePoint2=self.femurFirstCutFrontLineNode.GetNthControlPointPositionWorld(1)
            RealTimeFirstSideLinePoint1=self.femurRealTimeFirstCutSideLineNode.GetNthControlPointPositionWorld(0)
            RealTimeFirstSideLinePoint2=self.femurRealTimeFirstCutSideLineNode.GetNthControlPointPositionWorld(1)
            RealTimeFirstFrontLinePoint1=self.femurRealTimeFirstCutFrontLineNode.GetNthControlPointPositionWorld(0)
            RealTimeFirstFrontLinePoint2=self.femurRealTimeFirstCutFrontLineNode.GetNthControlPointPositionWorld(1)

            arrayPoint1=slicer.util.getNode('FemurPoints').GetNthControlPointPositionWorld(2)
            arrayPoint2=slicer.util.getNode('FemurPoints').GetNthControlPointPositionWorld(3)

            self.point_left_dict['point_presetline3d1'] = FirstSideLinePoint1
            self.point_left_dict['point_presetline3d2'] = FirstSideLinePoint2
            self.point_left_dict['point_realline3d1'] = RealTimeFirstSideLinePoint1
            self.point_left_dict['point_realline3d2'] = RealTimeFirstSideLinePoint2

            self.point_right_dict['point_presetline3d1'] = FirstFrontLinePoint1
            self.point_right_dict['point_presetline3d2'] = FirstFrontLinePoint2
            self.point_right_dict['point_realline3d1'] = RealTimeFirstFrontLinePoint1
            self.point_right_dict['point_realline3d2'] = RealTimeFirstFrontLinePoint2
            self.point_right_dict['point_downarrowpoint3d1'] = arrayPoint1
            self.point_right_dict['point_downarrowpoint3d2'] = arrayPoint2

            self.draw_line_actor(self.point_left_dict, self.point_right_dict)

            # 更新renderWindow
            self.threeDViews[0].threeDView().renderWindow().Render()
            self.threeDViews[1].threeDView().renderWindow().Render()

        elif type==2:

            #股骨第二截骨线
            self.state = 3
            SecondSideLinePoint1=self.femurSecondCutSideLineNode.GetNthControlPointPositionWorld(0)
            SecondSideLinePoint2=self.femurSecondCutSideLineNode.GetNthControlPointPositionWorld(1)
            SecondFrontLinePoint1=self.femurSecondCutFrontLineNode.GetNthControlPointPositionWorld(0)
            SecondFrontLinePoint2=self.femurSecondCutFrontLineNode.GetNthControlPointPositionWorld(1)
            RealTimeSecondSideLinePoint1=self.femurRealTimeSecondCutSideLineNode.GetNthControlPointPositionWorld(0)
            RealTimeSecondSideLinePoint2=self.femurRealTimeSecondCutSideLineNode.GetNthControlPointPositionWorld(1)
            RealTimeSecondFrontLinePoint1=self.femurRealTimeSecondCutFrontLineNode.GetNthControlPointPositionWorld(0)
            RealTimeSecondFrontLinePoint2=self.femurRealTimeSecondCutFrontLineNode.GetNthControlPointPositionWorld(1)

            ThirdFrontLinePoint1=self.femurThirdCutFrontLineNode.GetNthControlPointPositionWorld(0)
            ThirdFrontLinePoint2=self.femurThirdCutFrontLineNode.GetNthControlPointPositionWorld(1)
            RealTimeThirdFrontLinePoint1=self.femurRealTimeThirdCutFrontLineNode.GetNthControlPointPositionWorld(0)
            RealTimeThirdFrontLinePoint2=self.femurRealTimeThirdCutFrontLineNode.GetNthControlPointPositionWorld(1)

            arrayPoint1=slicer.util.getNode('FemurPoints').GetNthControlPointPositionWorld(1)
            arrayPoint2=slicer.util.getNode('FemurPoints').GetNthControlPointPositionWorld(2)

            self.point_left_dict['point_presetline3d1'] = SecondSideLinePoint1
            self.point_left_dict['point_presetline3d2'] = SecondSideLinePoint2
            self.point_left_dict['point_realline3d1'] = RealTimeSecondSideLinePoint1
            self.point_left_dict['point_realline3d2'] = RealTimeSecondSideLinePoint2
            self.point_left_dict['point_downarrowpoint3d1'] = SecondSideLinePoint1
            self.point_left_dict['point_uparrowpoint3d2'] = RealTimeSecondSideLinePoint1

            self.point_right_dict['point_presetline3d1'] = SecondFrontLinePoint1
            self.point_right_dict['point_presetline3d2'] = SecondFrontLinePoint2
            self.point_right_dict['point_realline3d1'] = RealTimeSecondFrontLinePoint1  
            self.point_right_dict['point_realline3d2'] = RealTimeSecondFrontLinePoint2


            self.point_right_dict['point_dashline3d1'] = ThirdFrontLinePoint1
            self.point_right_dict['point_dashline3d2'] = ThirdFrontLinePoint2
            self.point_right_dict['point_brokenline3d1'] = RealTimeThirdFrontLinePoint1
            self.point_right_dict['point_brokenline3d2'] = RealTimeThirdFrontLinePoint2

            # print("第一刀预设",SecondFrontLinePoint1,SecondFrontLinePoint2)
            # print("第二刀预设",ThirdFrontLinePoint1,ThirdFrontLinePoint2)

            self.draw_line_actor(self.point_left_dict, self.point_right_dict)

            # 更新renderWindow
            self.threeDViews[0].threeDView().renderWindow().Render()
            self.threeDViews[1].threeDView().renderWindow().Render()

    def updatacolor(self):
        color = [1, 1, 0 ]
        self.lineactor_left.updata_realanddash_color(color)
        self.lineactor_right.updata_realanddash_color(color)

        self.threeDViews[0].threeDView().renderWindow().Render()
        self.threeDViews[1].threeDView().renderWindow().Render()



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


    def project_point_to_plane(self,point, plane_node_name):
        # 获取平面节点
        plane_node = slicer.util.getNode(plane_node_name)
        
        # 获取平面参数
        origin = np.array(plane_node.GetOriginWorld())
        normal = np.array(plane_node.GetNormalWorld())
        
        # 计算点到平面的投影点
        point = np.array(point)
        point_to_origin = point - origin
        distance = np.dot(point_to_origin, normal)
        projection = point - distance * normal
        
        return projection

    
    # 停止绘制
    def pause_paint(self):
        self.is_pause = True

    def onChangeFemurTransBaseTibia(self, caller=None, event=None):
        # 定义文件路径
        log_file_path = os.path.join(os.path.dirname(__file__), "angle_data_log.txt")

        # 计算股骨工具相对于胫骨工具的变换，用于计算股骨的变换
        FemurTransNode = slicer.util.getNode('Femurtool_Transform')
        TibiaTransNode = slicer.util.getNode('Tibiatool_Transform')
        femurTransBaseTibiaNode = slicer.util.getNode('FemurTransBaseTibia')
        femurTrans = slicer.util.arrayFromTransformMatrix(FemurTransNode)
        tibiaTrans = slicer.util.arrayFromTransformMatrix(TibiaTransNode)
        FemurRealTrans = np.dot(femurTrans, self.FemurToRealTrans)
        TibiaToOriginTrans = np.dot(np.linalg.inv(self.TibiaToRealTrans), np.linalg.inv(tibiaTrans))
        TibiaToFemur = np.dot(TibiaToOriginTrans, FemurRealTrans)
        femurTransBaseTibiaNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(TibiaToFemur))
        minZInner, minZOuter = self.calculateLowestPointToTibiaCutPlane()
        angle = slicer.modules.kneeplane.widgetRepresentation().self().transToEuler(TibiaToFemur)


        if self.is_pause == False:
            # 如果这是第一次调用，直接保存当前角度
            if self.last_angle is None:
                self.last_angle = int(angle[0])
                self.last_minZInner = minZInner
                self.last_minZOuter = minZOuter

            # 计算当前角度与上一次角度的差值
            angle_diff = int(angle[0] - self.last_angle)

            # 打印上一次角度和值
            ## print("上一次左 右 角度", self.last_minZInner, self.last_minZOuter, self.last_angle)
            '''with open(log_file_path, "a") as file:
                file.write(f"上一次 左:{self.last_minZInner} 右:{self.last_minZOuter} 角度:{self.last_angle}\n")
            '''

            # 如果角度差值大于1度，进行插值
            if abs(angle_diff) > 1:
                num_steps = int(abs(angle_diff))  # 插值的步数
                for i in range(1, num_steps + 1):
                    interpolated_angle = self.last_angle + i * (angle_diff / num_steps)
                    interpolated_minZInner = minZInner + (self.last_minZInner - minZInner) / num_steps * (num_steps - i)
                    interpolated_minZOuter = minZOuter + (self.last_minZOuter - minZOuter) / num_steps * (num_steps - i)
                    if self.qMRML_widget is not None:
                        # 调用 paintCurve 模块，传入插值后的角度
                        slicer.modules.paintcurve.widgetRepresentation().self().curve_widget.modifyPoint(
                            (interpolated_minZInner, int(interpolated_angle)),
                            (interpolated_minZOuter, int(interpolated_angle))
                        )
                    # 写入数据到文件
                    '''with open(log_file_path, "a") as file:
                        file.write(f"插入左:{interpolated_minZInner} 右:{interpolated_minZOuter} 角度:{int(interpolated_angle)}\n")
                    '''
            # 最后绘制当前的角度
            if self.qMRML_widget is not None:
                slicer.modules.paintcurve.widgetRepresentation().self().curve_widget.modifyPoint(
                    (minZInner, int(angle[0])), (minZOuter, int(angle[0]))
                )

            ## print("当前左 右 角度", minZInner, minZOuter, int(angle[0]))

            # 写入当前数据到文件
            '''with open(log_file_path, "a") as file:
                file.write(f"当前左:{minZInner} 右:{minZOuter} 角度:{int(angle[0])}\n")
            '''
            # 更新 last_angle 为当前角度
            self.last_angle = int(angle[0])
            self.last_minZInner = minZInner
            self.last_minZOuter = minZOuter
            if abs(angle[0])<5:
                if self.isDrawFinished():
                    self.pause_paint()
            else:
                self.draw_time=0





    # 当度数小于5度持续5s时，判断是否绘制完成
    def isDrawFinished(self):
        lineValues1=slicer.modules.paintcurve.widgetRepresentation().self().curve_widget.getAllPoints()[0].copy()
        lineValues2=slicer.modules.paintcurve.widgetRepresentation().self().curve_widget.getAllPoints()[1].copy()
        # 计算lineValues1中的每个元素的第一个数，有多少不等于0的
        num1=len([value for value in lineValues1 if value[0]!=0])
        num2=len([value for value in lineValues2 if value[0]!=0])
        if num1>=90 and num2>=90:
            nowTime=time.time()
            if self.draw_time==0:
                self.draw_time=nowTime
                return False
            if nowTime-self.draw_time>5:
                self.draw_time=0
                # 记录曲线
                slicer.modules.kneeplane.widgetRepresentation().self().lineValues1=lineValues1
                slicer.modules.kneeplane.widgetRepresentation().self().lineValues2=lineValues2
                return True
            else:
                return False
        else:
            self.draw_time=0
            return False


        



    # 计算内外侧最低点到胫骨截骨面的距离
    def calculateLowestPointToTibiaCutPlane(self):
        # 获取胫骨假体的父级变换
        TibiaJTTransNode=slicer.util.getNode('TibiaTransNode')
        TibiaJTTrans=slicer.util.arrayFromTransformMatrix(TibiaJTTransNode)
        # 获取内侧最低点和外侧最低点
        lowestPointsInner=slicer.util.getNode('LowestPointsInner')
        lowestPointsOuter=slicer.util.getNode('LowestPointsOuter')
        num=lowestPointsInner.GetNumberOfControlPoints()
        PointsInner=[]
        PointsOuter=[]
        for i in range(num):
            point=np.append(np.array(lowestPointsInner.GetNthControlPointPositionWorld(i)),1)
            PointsInner.append(np.dot(TibiaJTTrans,point)[0:3])
        
        num=lowestPointsOuter.GetNumberOfControlPoints()
        for i in range(num):
            point=np.append(np.array(lowestPointsOuter.GetNthControlPointPositionWorld(i)),1)
            PointsOuter.append(np.dot(TibiaJTTrans,point)[0:3])

        # 获取PointsInner中Z的最小值
        minZInner=np.min([point[2] for point in PointsInner])
        minZOuter=np.min([point[2] for point in PointsOuter])
        return minZInner,minZOuter


    def onChangeJTFemur(self,modelNode):
        self.FemurModel=modelNode
        self.onShowModel(modelNode, self.threeDViews)
        modelActor=self.getModelActor(modelNode.GetName(),self.threeDViews[0])
        self.MoveActor(modelActor,self.threeDViews[0],self.rendererList[0])
        modelActor=self.getModelActor(modelNode.GetName(),self.threeDViews[1])
        self.MoveActor(modelActor,self.threeDViews[1],self.rendererList[2])

    def onChangeJTTibia(self,modelNode):
        self.TibiaModel=modelNode
        self.onShowModel(modelNode, self.threeDViews)


        # 设置模型在哪几个视图中显示
    def onShowModel(self, model, viewListShow):
        for view in viewListShow:
            model.GetDisplayNode().AddViewNodeID(view.mrmlViewNode().GetID())

    def getModelActor(self,modelName,targetWidget):
        # 获取 3D 渲染器
        renderer = targetWidget.threeDView().renderWindow().GetRenderers().GetFirstRenderer()

        # 获取模型节点
        modelNode = slicer.mrmlScene.GetFirstNodeByName(modelName)
        if not modelNode or not isinstance(modelNode, slicer.vtkMRMLModelNode):
            # print(f"Model {modelName} not found or is not a vtkMRMLModelNode!")
            return None

        # 获取模型的 PolyData
        modelPolyData = modelNode.GetPolyData()
        if not modelPolyData:
            # print(f"Model {modelName} has no PolyData!")
            return None
        bounds=modelPolyData.GetBounds()
        # 获取渲染器中的所有 actors
        actors = renderer.GetActors()
        actors.InitTraversal()  # 初始化遍历
        ## print(bounds)
        # 遍历每一个 vtkActor
        for i in range(actors.GetNumberOfItems()):
            actor = actors.GetNextActor()
            if not actor:
                continue

            if actor.GetBounds()==bounds:
                
                return actor  # 找到与模型对应的 actor

        # print(f"Actor for model {modelName} not found!")
        return None

    def MoveActor(self,actor,threeDViewWidget,newRenderer):
        renderWindow = threeDViewWidget.threeDView().renderWindow()
        # 获取源渲染器
        sourceRenderer = renderWindow.GetRenderers().GetFirstRenderer()
        
        # 复制源渲染器的相机设置
        newRenderer.SetActiveCamera(sourceRenderer.GetActiveCamera())

        # 从源渲染器中移除 actor
        sourceRenderer.RemoveActor(actor)

        # 将 actor 添加到新的 vtkRenderer
        newRenderer.AddActor(actor)
        #newRenderer.SetLayer(1)

        # 重新渲染
        renderWindow.Render()

    
    def updatePopWidgetPosition1(self):
        """更新3D视图的按钮位置"""
        self.viewButtonList[0].setPositionByWidget(self.threeDViews[0],'top')
        self.viewButtonList[1].setPositionByWidget(self.threeDViews[0],'bottom')
        self.viewButtonList[2].setPositionByWidget(self.threeDViews[1],'top')
        self.viewButtonList[3].setPositionByWidget(self.threeDViews[1],'bottom_left')
        self.viewButtonList[4].setPositionByWidget(self.threeDViews[1],'bottom_right')

        self.verifyLabel.setGeometry(self.widget_Top.width / 2 - 50, self.widget_Top.height / 2 - 50, 100, 100)
        '''# 设置进度条位置
        
        self.processBar.setGeometry(self.widget_Top.width / 2 - 100, self.widget_Top.height / 2 + 50, 200, 20)'''

    def updateTibiaJtTransNodeByTransform(self,transform):
        TibiaJTTransNode=slicer.util.getNode('TibiaJTTransNode')
        
        


    def draw_line_actor(self, point_left_dict, point_right_dict):
        
        if self.state == 0:
            # 只需要计算两个角度，不需要绘制线段
            self.lineactor_left.clear_actor_1(self.rendererList[0])
            self.lineactor_left.clear_actor_2(self.rendererList[1])
            self.lineactor_right.clear_actor_1(self.rendererList[2])
            self.lineactor_right.clear_actor_2(self.rendererList[3])
            # self.viewButtonList[0].CenterButton.setCenterNumber(11)
            # self.viewButtonList[2].CenterButton.setCenterNumber(11)
            self.viewButtonList[1].hide()
            self.viewButtonList[3].hide()
            self.viewButtonList[4].hide()
            self.verifyLabel.hide()
        
        elif self.state == 1:
            self.verifyLabel.show()
            self.viewButtonList[1].hide()
            self.viewButtonList[3].show()
            self.viewButtonList[4].show()

            self.lineactor_left.clear_actor_1(self.rendererList[0])
            self.lineactor_left.clear_actor_2(self.rendererList[1])
            self.lineactor_right.clear_actor_1(self.rendererList[2])
            self.lineactor_right.clear_actor_2(self.rendererList[3])

            # 左侧，只绘制两条线
            # self.viewButtonList[0].CenterButton.setCenterNumber(11)
            self.viewButtonList[0].CenterButton.setCenterText('post')
            renderer_left1 = self.rendererList[0]
            renderer_left2 = self.rendererList[1]
            point_left_dict = point_left_dict
            self.lineactor_left.draw_preset_Solid_line(renderer_left1, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])
            self.lineactor_left.draw_real_Solid_line(renderer_left1, point_left_dict['point_realline3d1'], point_left_dict['point_realline3d2'])
            self.lineactor_left.draw_alternating_line(renderer_left2, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])

            # 右侧，只绘制线和箭头
            point_right_dict = point_right_dict
            # self.viewButtonList[2].CenterButton.setCenterNumber(11)
            # self.viewButtonList[3].CenterButton.setCenterNumber(11)
            # self.viewButtonList[4].CenterButton.setCenterNumber(11)
            renderer_right1 = self.rendererList[2]
            renderer_right2 = self.rendererList[3]
            self.lineactor_right.draw_downward_arrow(renderer_right1, point_right_dict['point_downarrowpoint3d1'])
            self.lineactor_right.draw_downward_arrow(renderer_right1, point_right_dict['point_downarrowpoint3d2'])
            self.lineactor_right.draw_preset_Solid_line(renderer_right1, point_right_dict['point_presetline3d1'], point_right_dict['point_presetline3d2'])
            self.lineactor_right.draw_real_Solid_line(renderer_right1, point_right_dict['point_realline3d1'], point_right_dict['point_realline3d2'])
            self.lineactor_right.draw_alternating_line(renderer_right2, point_right_dict['point_presetline3d1'], point_right_dict['point_presetline3d2'])
            self.lineactor_right.draw_upward_arrow(renderer_right1, point_right_dict['point_realline3d1'])
            self.lineactor_right.draw_upward_arrow(renderer_right1, point_right_dict['point_realline3d2'])

        elif self.state == 2:
            self.verifyLabel.show()
            self.viewButtonList[1].hide()
            self.viewButtonList[3].show()
            self.viewButtonList[4].show()
            self.lineactor_left.clear_actor_1(self.rendererList[0])
            self.lineactor_left.clear_actor_2(self.rendererList[1])
            self.lineactor_right.clear_actor_1(self.rendererList[2])
            self.lineactor_right.clear_actor_2(self.rendererList[3])
            # 左侧，只绘制两条线
            # self.viewButtonList[0].CenterButton.setCenterNumber(11)
            self.viewButtonList[0].CenterButton.setCenterText('flex')
            renderer_left1 = self.rendererList[0]
            renderer_left2 = self.rendererList[1]
            point_left_dict = point_left_dict
            self.lineactor_left.draw_preset_Solid_line(renderer_left1, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])
            self.lineactor_left.draw_real_Solid_line(renderer_left1, point_left_dict['point_realline3d1'], point_left_dict['point_realline3d2'])
            self.lineactor_left.draw_alternating_line(renderer_left2, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])
            # 右侧，只绘制线和箭头
            point_right_dict = point_right_dict
            # self.viewButtonList[2].CenterButton.setCenterNumber(11)
            # self.viewButtonList[3].CenterButton.setCenterNumber(11)
            # self.viewButtonList[4].CenterButton.setCenterNumber(11)
            renderer_right1 = self.rendererList[2]
            renderer_right2 = self.rendererList[3]
            self.lineactor_right.draw_upward_arrow(renderer_right1, point_right_dict['point_downarrowpoint3d1'])
            self.lineactor_right.draw_upward_arrow(renderer_right1, point_right_dict['point_downarrowpoint3d2'])
            self.lineactor_right.draw_preset_Solid_line(renderer_right1, point_right_dict['point_presetline3d1'], point_right_dict['point_presetline3d2'])
            self.lineactor_right.draw_real_Solid_line(renderer_right1, point_right_dict['point_realline3d1'], point_right_dict['point_realline3d2'])
            self.lineactor_right.draw_alternating_line(renderer_right2, point_right_dict['point_presetline3d1'], point_right_dict['point_presetline3d2'])
            self.lineactor_right.draw_downward_arrow(renderer_right1, point_right_dict['point_realline3d1'])
            self.lineactor_right.draw_downward_arrow(renderer_right1, point_right_dict['point_realline3d2'])
        elif self.state == 3:
            self.verifyLabel.show()
            self.viewButtonList[1].show()
            self.viewButtonList[3].show()
            self.viewButtonList[4].show()
            # 给节点设置数字
            self.viewButtonList[0].CenterButton.setCenterText('flex')
            # self.viewButtonList[0].CenterButton.setCenterNumber(11)
            # self.viewButtonList[1].CenterButton.setCenterNumber(11)
            # self.viewButtonList[2].CenterButton.setCenterNumber(11)
            # self.viewButtonList[3].CenterButton.setCenterNumber(11)
            # self.viewButtonList[4].CenterButton.setCenterNumber(11)

            self.lineactor_left.clear_actor_1(self.rendererList[0])
            self.lineactor_left.clear_actor_2(self.rendererList[1])
            self.lineactor_right.clear_actor_1(self.rendererList[2])
            self.lineactor_right.clear_actor_2(self.rendererList[3])

            # 左侧，绘制两条线和箭头
            renderer_left1 = self.rendererList[0]
            renderer_left2 = self.rendererList[1]
            point_left_dict = point_left_dict
            self.lineactor_left.draw_preset_Solid_line(renderer_left1, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])
            self.lineactor_left.draw_real_Solid_line(renderer_left1, point_left_dict['point_realline3d1'], point_left_dict['point_realline3d2'])
            self.lineactor_left.draw_alternating_line(renderer_left2, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])
            self.lineactor_left.draw_downward_arrow(renderer_left1, point_left_dict['point_downarrowpoint3d1'])
            self.lineactor_left.draw_upward_arrow(renderer_left1, point_left_dict['point_uparrowpoint3d2'])

            # 右侧，绘制线和箭头
            point_right_dict = point_right_dict
            # self.viewButtonList[2].CenterButton.setCenterNumber(11)
            # self.viewButtonList[3].CenterButton.setCenterNumber(11)
            # self.viewButtonList[4].CenterButton.setCenterNumber(11)
            renderer_right1 = self.rendererList[2]
            renderer_right2 = self.rendererList[3]
            self.lineactor_right.draw_2d_broken_line(renderer_right1, point_right_dict['point_brokenline3d1'], point_right_dict['point_brokenline3d2'])
            self.lineactor_right.draw_2d_dashed_line(renderer_right1, point_right_dict['point_dashline3d1'], point_right_dict['point_dashline3d2'])
            self.lineactor_right.draw_downward_arrow(renderer_right1, point_right_dict['point_brokenline3d1'])
            self.lineactor_right.draw_downward_arrow(renderer_right1, point_right_dict['point_brokenline3d2'])
            self.lineactor_right.draw_preset_Solid_line(renderer_right1, point_right_dict['point_presetline3d1'], point_right_dict['point_presetline3d2'])
            self.lineactor_right.draw_real_Solid_line(renderer_right1, point_right_dict['point_realline3d1'], point_right_dict['point_realline3d2'])
            self.lineactor_right.draw_alternating_line(renderer_right2, point_right_dict['point_presetline3d1'], point_right_dict['point_presetline3d2'])
            self.lineactor_right.draw_upward_arrow(renderer_right1, point_right_dict['point_dashline3d1'])
            self.lineactor_right.draw_upward_arrow(renderer_right1, point_right_dict['point_dashline3d2'])

    
class rendereractor:
    def __init__(self):
        self.actor_map = []
        self.point_brokenline3d1 = 0   # 示例点，具体值根据实际情况设置
        self.point_brokenline3d2 = 0 # 示例点，具体值根据实际情况设置
        self.point_dashline3d1 = 0  # 示例点，具体值根据实际情况设置
        self.point_dashline3d2 = 0  # 示例点，具体值根据实际情况设置

        self.preset_actor_map = []
        #self.real_actor_map = []
        self.presetdash_actor_map = []

        # 两条实线，用于显示，一条实时，一条预设
        
        self.Realline_point3d1 = [0,0,0]
        self.Realline_point3d2 = [100, 100, 100]
        self.presetline_point3d1 = [0,0,0]
        self.presetline_point3d2 = [100, 100, 100]
        self.Realline_point2d1 = [0, 0]
        self.Realline_point2d2 = [0, 0]
        self.presetline_point2d1 = [0, 0]
        self.presetline_point2d2 = [0, 0]

    def updata_realanddash_color(self, color):
        for i in self.preset_actor_map:
            i.GetProperty().SetColor(color[0], color[1], color[2])
        
        for i in self.presetdash_actor_map:
            i.GetProperty().SetColor(color[0], color[1], color[2])


    def calcuate_distance(self, point1, point2):
        return math.sqrt((point2[0] - point1[0]) ** 2 + (point2[1] - point1[1]) ** 2)

    def clear_actor_1(self, renderer):

        for i in self.actor_map:
            renderer.RemoveActor2D(i)
        
        for i in self.preset_actor_map:
            renderer.RemoveActor2D(i)

    def clear_actor_2(self, renderer):

        for i in self.presetdash_actor_map:
            renderer.RemoveActor2D(i)


    def draw_real_Solid_line(self, renderer, point1_3d, point2_3d):

        # 将3D坐标转换为屏幕坐标
        point1_2d = self.convert_3d_to_2d(renderer, point1_3d)
        point2_2d = self.convert_3d_to_2d(renderer, point2_3d)

        self.Realline_point2d1 = point1_2d
        self.Realline_point2d2 = point2_2d

        # 计算断开前后两段线的端点
        # 创建点集合
        points = vtk.vtkPoints()
        points.InsertNextPoint(point1_2d[0], point1_2d[1], 0)  # 起点
        points.InsertNextPoint(point2_2d[0], point2_2d[1], 0)  # 终点

        # 创建线段
        lines = vtk.vtkCellArray()

        # 第一段线段：从起点到断开开始
        lines.InsertNextCell(2)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(1)

        # 第二段线段：从断开结束到终点
        lines.InsertNextCell(2)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(3)

        # 创建 PolyData
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(lines)

        # 创建 Mapper
        lineMapper = vtk.vtkPolyDataMapper2D()
        lineMapper.SetInputData(polyData)

        # 创建 Actor
        lineActor = vtk.vtkActor2D()
        lineActor.SetMapper(lineMapper)

        # 设置线条颜色和宽度
        lineActor.GetProperty().SetColor(0, 206/255, 209/255)
        lineActor.GetProperty().SetLineWidth(4)

        self.actor_map.append(lineActor)

        # 添加到渲染器
        renderer = renderer
        renderer.AddActor2D(lineActor)

    def draw_preset_Solid_line(self, renderer, point1_3d, point2_3d):

        # 将3D坐标转换为屏幕坐标
        point1_2d = self.convert_3d_to_2d(renderer, point1_3d)
        point2_2d = self.convert_3d_to_2d(renderer, point2_3d)

        self.presetline_point2d1 = point1_2d
        self.presetline_point2d2 = point2_2d

        # 创建点集合
        points = vtk.vtkPoints()
        points.InsertNextPoint(point1_2d[0], point1_2d[1], 0)  # 起点

        points.InsertNextPoint(point2_2d[0], point2_2d[1], 0)  # 终点

        # 创建线段
        lines = vtk.vtkCellArray()

        # 第一段线段：从起点到断开开始
        lines.InsertNextCell(2)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(1)

        # 第二段线段：从断开结束到终点
        lines.InsertNextCell(2)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(3)

        # 创建 PolyData
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(lines)

        # 创建 Mapper
        lineMapper = vtk.vtkPolyDataMapper2D()
        lineMapper.SetInputData(polyData)

        # 创建 Actor
        lineActor = vtk.vtkActor2D()
        lineActor.SetMapper(lineMapper)

        # 设置线条颜色和宽度
        lineActor.GetProperty().SetColor(1.0, 1.0, 1.0)  
        lineActor.GetProperty().SetLineWidth(4)

        self.preset_actor_map.append(lineActor)

        # 添加到渲染器
        renderer = renderer
        renderer.AddActor2D(lineActor)

    def draw_alternating_line(self, renderer, point1_3d, point2_3d, dash_length=20, gap_length=20):
        # 将3D坐标转换为屏幕坐标
        point1_2d = self.convert_3d_to_2d(renderer, point1_3d)
        point2_2d = self.convert_3d_to_2d(renderer, point2_3d)

        
        # 计算线段的总长度
        total_length = math.sqrt((point2_2d[0] - point1_2d[0]) ** 2 + (point2_2d[1] - point1_2d[1]) ** 2)
        if total_length == 0:
            return
        # 计算线段的单位向量
        direction_x = (point2_2d[0] - point1_2d[0]) / total_length
        direction_y = (point2_2d[1] - point1_2d[1]) / total_length

        # 创建线段
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()

        current_length = 0
        index = 0

        # 循环绘制虚线（线段和空白段）
        while current_length < total_length:
            # 计算当前线段的起点
            start_x = point1_2d[0] + direction_x * current_length
            start_y = point1_2d[1] + direction_y * current_length

            # 计算当前线段的终点，线段的长度为dash_length
            end_length = min(current_length + dash_length, total_length)
            end_x = point1_2d[0] + direction_x * end_length
            end_y = point1_2d[1] + direction_y * end_length

            # 添加起点和终点到点集中
            points.InsertNextPoint(start_x, start_y, 0)
            points.InsertNextPoint(end_x, end_y, 0)

            # 创建一个线段
            lines.InsertNextCell(2)
            lines.InsertCellPoint(index)
            lines.InsertCellPoint(index + 1)

            # 更新索引和长度
            index += 2
            current_length += dash_length + gap_length

        # 创建 PolyData
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(lines)

        # 创建 Mapper
        lineMapper = vtk.vtkPolyDataMapper2D()
        lineMapper.SetInputData(polyData)

        # 创建 Actor
        lineActor = vtk.vtkActor2D()
        lineActor.SetMapper(lineMapper)

        # 设置线条颜色
        lineActor.GetProperty().SetColor(1.0, 1.0, 1.0)  
        lineActor.GetProperty().SetLineWidth(4)

        self.presetdash_actor_map.append(lineActor)

        # 添加到3D视图的渲染器
        renderer = renderer
        renderer.AddActor2D(lineActor)


    def draw_2d_broken_line(self, renderer, point1_3d, point2_3d):

        # 将3D坐标转换为屏幕坐标
        point1_2d = self.convert_3d_to_2d(renderer, point1_3d)
        point2_2d = self.convert_3d_to_2d(renderer, point2_3d)

        # 计算线段向量 (point2 - point1)
        dx = point2_2d[0] - point1_2d[0]
        dy = point2_2d[1] - point1_2d[1]

        # 计算断开前后两段线的端点
        # 第一段结束点（前1/3处）
        break_start_2d = [point1_2d[0] + dx / 3, point1_2d[1] + dy / 3]
        # 第二段起点（后1/3处）
        break_end_2d = [point1_2d[0] + 2 * dx / 3, point1_2d[1] + 2 * dy / 3]

        # 创建点集合
        points = vtk.vtkPoints()
        points.InsertNextPoint(point1_2d[0] - dx / 5, point1_2d[1] - dy / 5, 0)  # 起点
        points.InsertNextPoint(break_start_2d[0], break_start_2d[1], 0)  # 断开前的点
        points.InsertNextPoint(break_end_2d[0], break_end_2d[1], 0)  # 断开后的点
        points.InsertNextPoint(point2_2d[0] + dx / 5, point2_2d[1] + dy / 5, 0)  # 终点

        # 创建线段
        lines = vtk.vtkCellArray()

        # 第一段线段：从起点到断开开始
        lines.InsertNextCell(2)
        lines.InsertCellPoint(0)
        lines.InsertCellPoint(1)

        # 第二段线段：从断开结束到终点
        lines.InsertNextCell(2)
        lines.InsertCellPoint(2)
        lines.InsertCellPoint(3)

        # 创建 PolyData
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(lines)

        # 创建 Mapper
        lineMapper = vtk.vtkPolyDataMapper2D()
        lineMapper.SetInputData(polyData)

        # 创建 Actor
        lineActor = vtk.vtkActor2D()
        lineActor.SetMapper(lineMapper)

        # 设置线条颜色和宽度
        lineActor.GetProperty().SetColor(0, 206/255, 209/255)  # 绿色
        lineActor.GetProperty().SetLineWidth(4)

        self.actor_map.append(lineActor)

        # 添加到渲染器
        renderer = renderer
        renderer.AddActor2D(lineActor)

        #绘制箭头
        #self.draw_downward_arrow(renderer, point1_2d)
        #self.draw_downward_arrow(renderer, point2_2d)


    def draw_2d_dashed_line(self, renderer, point1_3d, point2_3d, dash_length=20, gap_length=20):

        # 将3D坐标转换为屏幕坐标
        point1_2d = self.convert_3d_to_2d(renderer, point1_3d)
        point2_2d = self.convert_3d_to_2d(renderer, point2_3d)

        # 计算线段的总长度
        total_length = math.sqrt((point2_2d[0] - point1_2d[0]) ** 2 + (point2_2d[1] - point1_2d[1]) ** 2)
        
        # 计算线段的单位向量
        direction_x = (point2_2d[0] - point1_2d[0]) / total_length
        direction_y = (point2_2d[1] - point1_2d[1]) / total_length

        # 创建线段
        points = vtk.vtkPoints()
        lines = vtk.vtkCellArray()

        current_length = 0
        index = 0

        # 循环绘制虚线（线段和空白段）
        while current_length < total_length:
            # 计算当前线段的起点
            start_x = point1_2d[0] + direction_x * current_length
            start_y = point1_2d[1] + direction_y * current_length

            # 计算当前线段的终点，线段的长度为dash_length
            end_length = min(current_length + dash_length, total_length)
            end_x = point1_2d[0] + direction_x * end_length
            end_y = point1_2d[1] + direction_y * end_length

            # 添加起点和终点到点集中
            points.InsertNextPoint(start_x, start_y, 0)
            points.InsertNextPoint(end_x, end_y, 0)

            # 创建一个线段
            lines.InsertNextCell(2)
            lines.InsertCellPoint(index)
            lines.InsertCellPoint(index + 1)

            # 更新索引和长度
            index += 2
            current_length += dash_length + gap_length

        # 创建 PolyData
        polyData = vtk.vtkPolyData()
        polyData.SetPoints(points)
        polyData.SetLines(lines)

        # 创建 Mapper
        lineMapper = vtk.vtkPolyDataMapper2D()
        lineMapper.SetInputData(polyData)

        # 创建 Actor
        lineActor = vtk.vtkActor2D()
        lineActor.SetMapper(lineMapper)

        # 设置线条颜色
        lineActor.GetProperty().SetColor(1.0, 1.0, 1.0)  
        lineActor.GetProperty().SetLineWidth(4)

        self.actor_map.append(lineActor)

        # 添加到3D视图的渲染器
        renderer = renderer
        renderer.AddActor2D(lineActor)

        # 绘制箭头
        #self.draw_upward_arrow(renderer, point1_2d)

        #self.draw_upward_arrow(renderer, point2_2d)


    def convert_3d_to_2d(self, renderer, point3d):
        # 获取3D视图的摄像机矩阵
        renderer = renderer
        camera = renderer.GetActiveCamera()

        # 获取模型的世界坐标
        point_world = [point3d[0], point3d[1], point3d[2], 1.0]  # 齐次坐标

        # 转换为屏幕坐标
        displayCoord = [0.0, 0.0, 0.0]

        renderer.SetWorldPoint(point_world)
        renderer.WorldToDisplay()
        # 将世界坐标转换为显示坐标
        displayCoord = renderer.GetDisplayPoint()
        
        # print(f"worldCoord: {point_world}, displayCoord: {displayCoord}")

        return displayCoord[0:2]  # 返回 x, y 屏幕坐标
    
    # 在渲染器中添加箭头
    def draw_upward_arrow(self, renderer, tip_point_3d, arrow_length=50, arrow_width=10):
        tip_point = self.convert_3d_to_2d(renderer, tip_point_3d)
        direction = [0, 1]
        arrow_actor = ArrowActor2D(tip_point, direction,arrow_length, arrow_width)
        # 将箭头添加到渲染器中
        self.actor_map.append(arrow_actor)
        renderer.AddActor2D(arrow_actor)
        

    def draw_downward_arrow(self, renderer, tip_point_3d, arrow_length=50, arrow_width=10):
        tip_point = self.convert_3d_to_2d(renderer, tip_point_3d)
        direction = [0, -1]
        arrow_actor = ArrowActor2D(tip_point, direction,arrow_length, arrow_width)
        # 将箭头添加到渲染器中
        self.actor_map.append(arrow_actor)
        renderer.AddActor2D(arrow_actor)




class ArrowActor2D(vtk.vtkActor2D):
    def __init__(self, tip_point, direction, arrow_length=50.0, arrow_width=10.0):
        super().__init__()

        # 创建一个箭头源
        arrow_source = vtk.vtkArrowSource()
        arrow_source.Update()  # 更新箭头源

        # 创建 glyph filter
        glyph_filter = vtk.vtkGlyph2D()
        glyph_filter.SetSourceConnection(arrow_source.GetOutputPort())
        glyph_filter.SetScaleFactor(arrow_length)  # 设置箭头长度
        glyph_filter.OrientOn()
        glyph_filter.SetVectorModeToUseVector()  # 使用矢量方向

        # 确保 tip_point 是 3D 点
        if len(tip_point) == 2 and direction == [0, 1]:
            tip_point = (tip_point[0], tip_point[1] - arrow_length, 0.0)  # 添加 z 坐标为 0
        elif len(tip_point) == 2 and direction == [0, -1]:
            tip_point = (tip_point[0], tip_point[1] + arrow_length, 0.0)  # 添加 z 坐标为 0
    
        # 计算箭头的方向向量
        vector = np.array(direction, dtype=float)  # 明确指定数据类型为 float
        vector_length = np.linalg.norm(vector)
        if vector_length > 0:
            vector /= vector_length  # 归一化方向向量


        # 创建点数据，设置箭头的起点和终点
        points = vtk.vtkPoints()
        vectors = vtk.vtkDoubleArray()
        vectors.SetNumberOfComponents(3)  # 3D 向量

        # 插入起点和方向向量
        points.InsertNextPoint(tip_point[0], tip_point[1], tip_point[2])  # 只插入起点
        vectors.InsertNextTuple3(vector[0], vector[1], 0.0)  # 设置方向向量

        

        # 创建一个 PolyData 用于存储点和向量
        poly_data = vtk.vtkPolyData()
        poly_data.SetPoints(points)
        poly_data.GetPointData().SetVectors(vectors)

        glyph_filter.SetInputData(poly_data)  # 设置输入数据
        glyph_filter.Update()  # 更新 glyph filter

        # 创建 mapper
        mapper = vtk.vtkPolyDataMapper2D()
        mapper.SetInputConnection(glyph_filter.GetOutputPort())

        # 设置 mapper 到 actor
        self.SetMapper(mapper)

        # 设置箭头的颜色
        self.GetProperty().SetColor(1.0, 1.0, 1.0)  # 设置箭头颜色为红色


class CustomWindow(qt.QWidget):
    def __init__(self):
        super().__init__()
    def resizeEvent(self, event):
        slicer.modules.surgical_navigation.widgetRepresentation().self().updatePopWidgetPosition1()

class VerifyLabel(qt.QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.Verify_label = qt.QLabel(self)
        self.Verify_label.setStyleSheet('font-size: 50px; color: rgb(255, 170, 0); font: bold "黑体";')
        self.text_label = qt.QLabel(self)
        self.text_label.setStyleSheet('font-size: 24px; color: rgb(255, 170, 0); font: bold "黑体";')
        self.initUI()
        

    def initUI(self):
        layout = qt.QVBoxLayout(self)
        self.setLayout(layout)
        self.setStyleSheet("background-color: rgb(94, 94, 94); border-radius: 10px; border-color: rgb(0, 0, 0);")
        self.Verify_label.setText("√")
        self.text_label.setText("Verify")
        self.Verify_label.setAlignment(qt.Qt.AlignCenter)
        self.text_label.setAlignment(qt.Qt.AlignCenter)
        layout.addWidget(self.Verify_label)
        layout.addWidget(self.text_label)

        #设置layout
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.layout().setSpacing(0)



# 自定义进度条，设置接口
class TransparentProgressBar(qt.QProgressBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()
    def initUI(self):
        # 设置进度条样式
        self.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                background-color: rgba(0, 0, 0, 0);  /* 背景透明 */
            }
            QProgressBar::chunk {
                background-color: orange;  /* 进度条增长颜色为橙色 */
                width: 10px;
            }
        """)
        self.setRange(0, 100)  # 设置进度条范围
        self.setValue(0)  # 设置进度条初始值
        self.setAttribute(qt.Qt.WA_TranslucentBackground, True)


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

    # 切换文本颜色为蓝色或白色
    def setTextColor(self, type):
        if type == 'blue':
            self.number_label.setStyleSheet("font-size: 24px;color: blue;")
            self.unit_label.setStyleSheet("color: blue;")
        elif type == 'white':
            self.number_label.setStyleSheet("font-size: 24px;color: white;")
            self.unit_label.setStyleSheet("color: white;")

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

    # 切换文本颜色为蓝色或白色
    def setTextColor(self, type):
        self.center_text_label.setTextColor(type)
        # 设置按钮边框颜色
        if type == 'blue':
            self.setStyleSheet("QPushButton {background-color: transparent; border: 2px solid blue; color: blue; border-radius: 20px;}")
        elif type == 'white':
            self.setStyleSheet("QPushButton {background-color: transparent; border: 2px solid lightgray; color: white; border-radius: 20px;}")


class ViewPopWidget1(qt.QWidget):
    def __init__(self, type):
        super().__init__()
        self.type = type
        self.initUI()

    def initUI(self):
        # 创建布局
        layout = qt.QHBoxLayout()
        self.setMaximumWidth(320)
        self.setMaximumHeight(60)

        if self.type == 1:
            self.CenterButton = CustomButton_one('flex', self)
            self.CenterButton.setMaximumWidth(100)
            self.CenterButton.setMinimumWidth(100)
        
        elif self.type == 2:
            self.CenterButton = CustomButton_one('mm', self)
            self.CenterButton.setMaximumWidth(100)
            self.CenterButton.setMinimumWidth(100)

        elif self.type == 3:
            self.CenterButton = CustomButton_one('post', self)
            self.CenterButton.setMaximumWidth(100)
            self.CenterButton.setMinimumWidth(100)

        elif self.type == 4:
            self.CenterButton = CustomButton_one('int', self)
            self.CenterButton.setMaximumWidth(100)
            self.CenterButton.setMinimumWidth(100)


        self.CenterButton.setMinimumHeight(50)
        layout.addWidget(self.CenterButton)
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
        self.CenterButton.setStyleSheet(button_style)


    def setPositionByWidget(self, widget, TopOrBottom):
        # 获取所给窗口的位置和大小
        widget_geometry = widget.geometry
        widget_width = widget_geometry.width()
        widget_height = widget_geometry.height()

        # 获取本窗口的大小
        self_width = self.width
        self_height = self.height

        ## print(widget_width, widget_height, self_width, self_height)

        # 计算本窗口的位置
        if TopOrBottom == 'top':
            x = (widget_width ) / 2 - self_width / 2
            y = widget_height / 3 - self_height
        elif TopOrBottom == 'bottom':
            x = (widget_width ) / 2 - self_width / 2
            y = widget_height * 2 / 3

        elif TopOrBottom == 'bottom_left':
            x = (widget_width ) / 2 - self_width / 2 - 100
            y = widget_height * 2 / 3
        
        elif TopOrBottom == 'bottom_right':
            x = (widget_width ) / 2 - self_width / 2 + 100
            y = widget_height * 2 / 3

        ## print(x, y)
        # 设置本窗口的位置
        self.move(x, y)
                # 记录左右侧按钮的位置



#
# Surgical_NavigationLogic
#


class Surgical_NavigationLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self) -> None:
        """Called when the logic class is instantiated. Can be used for initializing member variables."""
        ScriptedLoadableModuleLogic.__init__(self)

    


    def creatCordinate(self, pointCenter, pointInner, pointOuter, pointA):
        XAxis = np.array(pointOuter) - np.array(pointInner)
        XAxis = XAxis / np.linalg.norm(XAxis)
        YAxis = np.array(pointA) - np.array(pointCenter)
        YAxis = YAxis / np.linalg.norm(YAxis)

        ZAxis = np.cross(XAxis, YAxis)
        ZAxis = ZAxis / np.linalg.norm(ZAxis)
        YAxis = np.cross(ZAxis, XAxis)
        YAxis = YAxis / np.linalg.norm(YAxis)

        # 创建坐标系，4*4矩阵，前三列为坐标系的三个轴，最后一列为原点
        matrix = np.eye(4)
        matrix[0:3, 0] = XAxis
        matrix[0:3, 1] = YAxis
        matrix[0:3, 2] = ZAxis
        matrix[0:3, 3] = np.array(pointCenter)
        return matrix


    def getTransformedPoint(self, point, matrix):
        # 将点转换到新的坐标系
        point = np.array(point)
        point = np.append(point, 1)
        point = np.dot(matrix, point)
        return point[0:3]