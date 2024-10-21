import logging
import math
import os
from typing import Annotated, Optional

import numpy as np
import qt
import slicer.util
import vtk

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

        self.state = 1 #三种状态0，1，2

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

        # 设置Verifylabel位置
        self.verifyLabel = VerifyLabel(self.widget_Top)
        self.verifyLabel.setGeometry(self.widget_Top.width / 2 - 50, self.widget_Top.height / 2 - 50, 100, 100)

        # 设置进度条位置
        self.processBar = TransparentProgressBar(self.widget_Top)
        self.processBar.setGeometry(self.widget_Top.width / 2 - 100, self.widget_Top.height / 2 + 50, 200, 20)
            
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



    # 进入导航模式
    def onEnterNavigation(self):
        if (self.femurTransBaseTibiaNode==None):
            self.FemurModel=slicer.util.getNode('FemurModel')
            self.TibiaModel=slicer.util.getNode('TibiaModel')
            # 设置为以骨骼为根坐标系
            # 计算股骨工具相对于胫骨工具的变换，用于计算股骨的变换
            
            self.femurTransBaseTibiaNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode")
            self.femurTransBaseTibiaNode.SetName("FemurTransBaseTibia")
            FemurTransNode=slicer.util.getNode('FemurTransNode')

            # 添加观察者
            FemurTransNode.AddObserver(self.femurTransBaseTibiaNode.TransformModifiedEvent, self.onChangeFemurTransBaseTibia)

            # 创建规划的线
            self.initLineNode(0)

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
        # 将FemurJTTransNode设置在self.femurTransBaseTibiaNode下
        FemurJTTransNode.SetAndObserveTransformNodeID(self.femurTransBaseTibiaNode.GetID())
        
        # 更新绘制规划的线
        self.initLineNode(1)

    def create_line_node(self,name, visibility, parent_node_id):
        line_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsLineNode")
        line_node.SetName(name)
        line_node.GetDisplayNode().SetVisibility(visibility)
        line_node.SetAndObserveTransformNodeID(parent_node_id)
        return line_node

    def setLinePoints(self,node1,node2,point1,point2):
        node1.RemoveAllControlPoints()
        node2.RemoveAllControlPoints()
        node1.AddControlPointWorld(point1)
        node1.AddControlPointWorld(point2)
        node2.AddControlPointWorld(point1)
        node2.AddControlPointWorld(point2)


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
            SideLinePoint1=self.tibiaCutSideLineNode.GetNthControlPointPositionWorld(0)
            SideLinePoint2=self.tibiaCutSideLineNode.GetNthControlPointPositionWorld(1)
            FrontLinePoint1=self.tibiaCutFrontLineNode.GetNthControlPointPositionWorld(0)
            FrontLinePoint2=self.tibiaCutFrontLineNode.GetNthControlPointPositionWorld(1)
            realTimeSideLinePoint1=self.tibiaRealTimeCutSideLineNode.GetNthControlPointPositionWorld(0)
            realTimeSideLinePoint2=self.tibiaRealTimeCutSideLineNode.GetNthControlPointPositionWorld(1)
            realTimeFrontLinePoint1=self.tibiaRealTimeCutFrontLineNode.GetNthControlPointPositionWorld(0)
            realTimeFrontLinePoint2=self.tibiaRealTimeCutFrontLineNode.GetNthControlPointPositionWorld(1)

            arrayPoint1=slicer.util.getNode('TibiaPoints').GetNthControlPointPositionWorld(1)
            arrayPoint2=slicer.util.getNode('TibiaPoints').GetNthControlPointPositionWorld(2)
            
            self.point_left_dict['point_presetline3d1'] = SideLinePoint1
            self.point_left_dict['point_presetline3d2'] = SideLinePoint2
            self.point_left_dict['point_realline3d1'] = realTimeSideLinePoint1
            self.point_left_dict['point_realline3d2'] = realTimeSideLinePoint2

            self.point_right_dict['point_presetline3d1'] = FrontLinePoint1
            self.point_right_dict['point_presetline3d2'] = FrontLinePoint2
            self.point_right_dict['point_realline3d1'] = realTimeFrontLinePoint1
            self.point_right_dict['point_realline3d2'] = realTimeFrontLinePoint2

            self.point_right_dict['point_downarrowpoint3d1'] = arrayPoint1
            self.point_right_dict['point_downarrowpoint3d2'] = arrayPoint2

            self.draw_line_actor(self.point_left_dict, self.point_right_dict)

            # 更新renderWindow
            self.threeDViews[0].threeDView().renderWindow().Render()
            self.threeDViews[1].threeDView().renderWindow().Render()

            
        elif type==1:
            FirstSideLinePoint1=self.femurFirstCutSideLineNode.GetNthControlPointPositionWorld(0)
            FirstSideLinePoint2=self.femurFirstCutSideLineNode.GetNthControlPointPositionWorld(1)
            FirstFrontLinePoint1=self.femurFirstCutFrontLineNode.GetNthControlPointPositionWorld(0)
            FirstFrontLinePoint2=self.femurFirstCutFrontLineNode.GetNthControlPointPositionWorld(1)
            arrayPoint1=slicer.util.getNode('FemurPoints').GetNthControlPointPositionWorld(1)
            arrayPoint2=slicer.util.getNode('FemurPoints').GetNthControlPointPositionWorld(2)

        elif type==2:
            SecondSideLinePoint1=self.femurSecondCutSideLineNode.GetNthControlPointPositionWorld(0)
            SecondSideLinePoint2=self.femurSecondCutSideLineNode.GetNthControlPointPositionWorld(1)
            SecondFrontLinePoint1=self.femurSecondCutFrontLineNode.GetNthControlPointPositionWorld(0)
            SecondFrontLinePoint2=self.femurSecondCutFrontLineNode.GetNthControlPointPositionWorld(1)


    def updatacolor(self):
        color = [1, 1, 0 ]
        self.lineactor_left.updata_realanddash_color(color)
        self.lineactor_right.updata_realanddash_color(color)

        self.threeDViews[0].threeDView().renderWindow().Render()
        self.threeDViews[1].threeDView().renderWindow().Render()

    def onEnterPlanning(self):
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


    def onChangeFemurTransBaseTibia(self,caller,event):
        # 计算股骨工具相对于胫骨工具的变换，用于计算股骨的变换
        FemurTransNode=slicer.util.getNode('FemurTransForm')
        TibiaTransNode=slicer.util.getNode('TibiaTransForm')
        femurTransBaseTibiaNode=slicer.util.getNode('FemurTransBaseTibia')
        femurTrans=slicer.util.arrayFromTransformMatrix(FemurTransNode)
        tibiaTrans=slicer.util.arrayFromTransformMatrix(TibiaTransNode)
        femurTransBaseTibiaNode.SetMatrixTransformToParent(slicer.util.vtkMatrixFromArray(np.dot(np.linalg.inv(tibiaTrans),femurTrans)))





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
            print(f"Model {modelName} not found or is not a vtkMRMLModelNode!")
            return None

        # 获取模型的 PolyData
        modelPolyData = modelNode.GetPolyData()
        if not modelPolyData:
            print(f"Model {modelName} has no PolyData!")
            return None
        bounds=modelPolyData.GetBounds()
        # 获取渲染器中的所有 actors
        actors = renderer.GetActors()
        actors.InitTraversal()  # 初始化遍历
        print(bounds)
        # 遍历每一个 vtkActor
        for i in range(actors.GetNumberOfItems()):
            actor = actors.GetNextActor()
            if not actor:
                continue

            if actor.GetBounds()==bounds:
                
                return actor  # 找到与模型对应的 actor

        print(f"Actor for model {modelName} not found!")
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


    def draw_line_actor(self, point_left_dict, point_right_dict):
        
        if self.state == 0:
            # 只需要计算两个角度，不需要绘制线段
            self.lineactor_left.clear_actor_1(self.rendererList[0])
            self.lineactor_left.clear_actor_2(self.rendererList[1])
            self.lineactor_right.clear_actor_1(self.rendererList[2])
            self.lineactor_right.clear_actor_2(self.rendererList[3])
            self.viewButtonList[0].CenterButton.setCenterNumber(11)
            self.viewButtonList[2].CenterButton.setCenterNumber(11)
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
            self.viewButtonList[0].CenterButton.setCenterNumber(11)
            self.viewButtonList[0].CenterButton.setCenterText('post')
            renderer_left1 = self.rendererList[0]
            renderer_left2 = self.rendererList[1]
            point_left_dict = point_left_dict
            self.lineactor_left.draw_preset_Solid_line(renderer_left1, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])
            self.lineactor_left.draw_real_Solid_line(renderer_left1, point_left_dict['point_realline3d1'], point_left_dict['point_realline3d2'])
            self.lineactor_left.draw_alternating_line(renderer_left2, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])

            # 右侧，只绘制线和箭头
            point_right_dict = point_right_dict
            self.viewButtonList[2].CenterButton.setCenterNumber(11)
            self.viewButtonList[3].CenterButton.setCenterNumber(11)
            self.viewButtonList[4].CenterButton.setCenterNumber(11)
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
            self.viewButtonList[0].CenterButton.setCenterNumber(11)
            self.viewButtonList[0].CenterButton.setCenterText('flex')
            renderer_left1 = self.rendererList[0]
            renderer_left2 = self.rendererList[1]
            point_left_dict = point_left_dict
            self.lineactor_left.draw_preset_Solid_line(renderer_left1, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])
            self.lineactor_left.draw_real_Solid_line(renderer_left1, point_left_dict['point_realline3d1'], point_left_dict['point_realline3d2'])
            self.lineactor_left.draw_alternating_line(renderer_left2, point_left_dict['point_presetline3d1'], point_left_dict['point_presetline3d2'])

            # 右侧，只绘制线和箭头
            point_right_dict = point_right_dict
            self.viewButtonList[2].CenterButton.setCenterNumber(11)
            self.viewButtonList[3].CenterButton.setCenterNumber(11)
            self.viewButtonList[4].CenterButton.setCenterNumber(11)
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
            self.viewButtonList[0].CenterButton.setCenterNumber(11)
            self.viewButtonList[1].CenterButton.setCenterNumber(11)
            self.viewButtonList[2].CenterButton.setCenterNumber(11)
            self.viewButtonList[3].CenterButton.setCenterNumber(11)
            self.viewButtonList[4].CenterButton.setCenterNumber(11)

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
            self.viewButtonList[2].CenterButton.setCenterNumber(11)
            self.viewButtonList[3].CenterButton.setCenterNumber(11)
            self.viewButtonList[4].CenterButton.setCenterNumber(11)
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
        
        print(f"worldCoord: {point_world}, displayCoord: {displayCoord}")

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

        print(widget_width, widget_height, self_width, self_height)

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

        print(x, y)
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

    
