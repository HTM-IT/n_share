# -*- coding: utf-8 -*-
import sys
import re
import math

import maya.cmds as mc
import maya.api.OpenMaya as om2
import maya.OpenMayaAnim as oma
import maya.OpenMaya as om
#from hi_tools.hi_utility import Decorators


class HTM_FreezeJoint:
    """ Function set of freezing joint orientation/rotation
    """
    @staticmethod
    @Decorators.undo_ctx
    def freeze_joint(freeze_rot=True, hierarchy=True):
        """ Set joint orient value to zero.

        Param:
            freeze_rot(bool):
            hierarchy(bool):
        """
        joints = mc.ls(sl=1, type='joint', l=1)
        if hierarchy:
            joints += mc.listRelatives(mc.ls(sl=1), ad=1, type='joint', f=1)
            joints = set(joints)  # delete redundant nodes

        for joint in joints:
            # Freeze joint orient
            mtx = mc.getAttr('{}.worldMatrix[0]'.format(joint))
            mtx = om2.MMatrix(mtx)
            rot_rad = om2.MTransformationMatrix(mtx).rotation()
            rot_deg = [math.degrees(x) for x in rot_rad]

            mc.setAttr('%s.jointOrient' % joint, 0, 0, 0)
            mc.xform(joint, ws=True, ro=rot_deg)

            # Freeze joint rotation
            if freeze_rot:
                rot = mc.xform(joint, q=True, ws=False, ro=True)
                mc.xform(joint, ro=(0, 0, 0))
                mc.setAttr('{}.jointOrient'.format(joint), *rot)

    @staticmethod
    def search_unfreezed_joint(mode='rotation'):
        """ Search joints whose rotation/orient is not zero.

        Param:
            mode(str): switch mode, rotation/orient

        Return:
            unfreezed(list): A list of joints found.
        """
        joints = mc.ls(type='joint', l=True)
        unfreezed = []
        if mode == 'rotation':
            for joint in joints:
                if not [0.0, 0.0, 0.0] == mc.xform(joint, q=True, ws=False, ro=True):
                    unfreezed.append(joint)
        elif mode == 'orient':
            for joint in joints:
                if not (0.0, 0.0, 0.0) == mc.getAttr(joint + '.jointOrient')[0]:
                    unfreezed.append(joint)
        mc.select(unfreezed, r=True)
        return unfreezed


class HTM_ReinitializeSkinnedJoint:
    """
    """
    @staticmethod
    @Decorators.undo_ctx
    def reinitialize():
        """ Set current joint toransformation as BindPose
        """
        selected = mc.ls(sl=True, type='joint', l=1)
        childlen = mc.listRelatives(ad=True, type='joint', f=1)
        parents = mc.listRelatives(p=True, type='joint', f=1)

        joints = []
        joints += selected
        joints += childlen if childlen else []
        joints += parents if parents else []

        if not selected:
            mc.error('Please select at least one joint')

        for j in joints:
            # get all skin cluster connecting to the joint
            sc_temp_list = mc.listConnections('{}.worldMatrix'.format(j), d=True, p=True, type='skinCluster')
            if not sc_temp_list:
                continue

            # get joint's matrix
            mtx_ws = mc.getAttr('{}.worldMatrix'.format(j))
            mtx_os = mc.xform(j, q=1, os=1, m=1)
            mtx_inv = mc.getAttr('{}.worldInverseMatrix'.format(j))

            # process per joints
            mc.setAttr('{}.bindPose'.format(j), mtx_ws, type='matrix')

            # bind pose info
            plugs = mc.listConnections(j, d=True, p=True, type = 'dagPose')
            if not plugs:
                continue
            dagpose = plugs[0].split('.')[0]
            plug_id = int(plugs[0].split('[')[-1][:-1])
            # bp_temp = mc.listConnections('{}.bindPose'.format(j), d=True, p=True)[0]
            # bp = bp_temp.split('.')[0]
            # bp_plug_id = re.findall(r"\d+", bp_temp)[-1]

            # reset bind pose
            mc.setAttr('{}.xformMatrix[{}]'.format(dagpose, plug_id), mtx_os, type='matrix')

            for sc_temp in sc_temp_list:
                # skin cluster info
                sc = sc_temp.split('.')[0]
                sc_plug_id = int(sc_temp.split('[')[-1][:-1])
                # sc_plug_id = re.findall(r"\d+", sc_temp)[-1]

                # reset initial position
                mc.setAttr('{}.bindPreMatrix[{}]'.format(sc, sc_plug_id), mtx_inv, type='matrix')

        mc.select(selected, r=1)

    @staticmethod
    def sc_envelope_toggle():
        """
        """
        sc_list = mc.ls(type='skinCluster')
        for sc in sc_list:
            if mc.getAttr(sc + '.envelope') == 0:
                # Set all SC envelope at 1, if even one SC whose envelope is 0 was found.
                for sc2 in sc_list:
                    mc.setAttr(sc2 + '.envelope', 1)
                return
            else:
                mc.setAttr(sc + '.envelope', 0)