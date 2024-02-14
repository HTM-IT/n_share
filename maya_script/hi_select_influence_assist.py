import maya.cmds as mc
import maya.mel as mel
import maya.api.OpenMaya as om2

class InfluenceTools:
    """
    """
    def __init__(self):
        # artCommand name is difined in
        # C:\Program Files\Autodesk\Maya2020\scripts\others\artAttrSkinCallback.mel
        self.art_command = 'artAttrSkinPaintCtx'

        # Get paint weight tools's ui name
        self.paint_weight_ui = ''
        self.update_paint_weight_ui_name()

        # Others
        self.infs_this_tool = []
        self.selected_influences = []
        self.tsl_name = ''


    def get_skin_cluster(self, node, weighted_only=False):
        sc = mel.eval('findRelatedSkinCluster("{}")'.format(node))
        #shape = mc.listRelatives(node, s=True, ni=True)
        #sc = mc.ls(mc.listConnections(shape, s=True, d=False), type='skinCluster')
        if sc:
            if weighted_only:
                infs = mc.skinCluster(sc, q=True, wi=True)
            else:
                infs = mc.skinCluster(sc, q=True, inf=True)
        else:
            infs = []

        return sc, infs


    def update_paint_weight_ui_name(self):
        try:
            current = mel.eval('string $tmp = $gArtSkinInfluencesList;')
        except:
            om2.MGlobal.displayError('Paint Skin Weight Tool was not found.')
            return

        if self.paint_weight_ui == current:
            return
        else:
            self.paint_weight_ui = current


    def check_influences(self):
        infs_paint_weight_ui = mc.treeView(self.paint_weight_ui, q=True, item=True, ch='')

        for inf in self.infs_this_tool[:]:
            if inf not in infs_paint_weight_ui:
                self.infs_this_tool.remove(inf)


    def sel_items(self):
        # Show Tool Properties
        mel.eval('ArtPaintSkinWeightsTool;')

        # Clear Selection
        self.update_paint_weight_ui_name()
        mc.treeView(self.paint_weight_ui, e=True, cs=True)
        infs_paint_weight_ui = mc.treeView(self.paint_weight_ui, q=True, item=True, ch='')

        # Get only one selected item
        item = mc.textScrollList(self.tsl_name, q=True, si=True)[-1] # get selected item id
        item = item.split(' ')[-1]
        self.selected_influences = item

        #for item in item:
        mc.treeView(self.paint_weight_ui, e=True, si=[item, True])

        # Update Paint Selection
        try:
            mel.eval('artSkinSelectInfluence("{}", "{}")'.format(self.art_command, item))
        except:
            om2.MGlobal.displayWarning('Please open Paint Skin Weight Tool.')
            return


    def clear_items(self):
        mc.treeView(self.paint_weight_ui, e=True, cs=True)
        mc.textScrollList(self.tsl_name, e=True, ra=True)


    def get_items(self, hierarchy=False):
        # First of all, clear the items
        mc.textScrollList(self.tsl_name, e=True, ra=True)

        if hierarchy:
            # Redundant name is not available for now.
            joints = mc.ls(sl=True, dag=True, type='joint', l=False)

        else:
            joints = mc.ls(sl=True, type='joint', l=True)


        # Remove joints that is not used as influences.
        infs_temp = []
        for j in joints:
            sc = mc.listConnections(j, d=True, s=False, type='skinCluster')
            if sc:
                infs_temp.append(j)

        self.infs_this_tool = [inf.split('|')[-1] for inf in infs_temp]

        # Get minimum of the node in outliner hierarchy.
        root = sorted(joints, key=lambda x: x.count('|'))[0]
        min_depth = root.count('|')

        infs_moified = []
        for inf in infs_temp:
            depth = inf.count('|') - min_depth
            pure_name = inf.split('|')[-1]
            new_name = ('- ' * depth) + pure_name
            infs_moified.append(new_name)

        for inf in infs_moified:
            mc.textScrollList(self.tsl_name, e=True, a=inf)


    def add_items(self):
        items = mc.textScrollList(self.tsl_name, q=True, si=True)

        joints = mc.ls(sl=True, type='joint')
        for j in joints[:]:
            if j in items:
                joints.remove(j)

        influences_temp = []
        for j in joints:
            sc = mc.listConnections(j, d=True, s=False, type='skinCluster')
            if sc:
                influences_temp.append(j)

        self.infs_this_tool = influences_temp
        for inf in self.infs_this_tool:
            mc.textScrollList(self.tsl_name, e=True, a=inf)


def hi_influence_select_tools():
    if mc.window('hi_influence_select_assist_win', exists = True) == True:
        mc.deleteUI('hi_influence_select_assist_win')

    # init function set
    inf_tools = InfluenceTools()

    mc.window('hi_influence_select_assist_win', t = 'hi select assist',
               mnb=False, mxb=False)

    mc.columnLayout()
    mc.text(l = '■ Influence List', fn = 'boldLabelFont')
    inf_tools.tsl_name = mc.textScrollList(h=300, w=306, ams=False, sc=inf_tools.sel_items)

    mc.text(l = '■ Edit Influence List', fn = 'boldLabelFont')
    mc.rowLayout(nc=3, ad3=3)
    mc.button(label='Get', c=inf_tools.get_items)
    mc.button(label='Get (Hierarchy)', c=lambda *args:inf_tools.get_items(True))
    mc.button(label='Add', c=inf_tools.add_items)
    mc.setParent('..')
    mc.button(label='Clear', c=inf_tools.clear_items)

    """
    If you want to use lambda, follow the example below.
    ex : mc.button(label='Clear', c=lambda *args:inf_tools.clear_items(tsl))
    """
    mc.setParent('..')

    #main layout end
    mc.showWindow('hi_influence_select_assist_win')


hi_influence_select_tools()