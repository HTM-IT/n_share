def transfer_skin_bind(copymode='ClosestPoint'):
    """ Smooth binding dst object using the same option and influences of src object

    Param:
        mode(str):'closestPoint', 'rayCast', 'uv', 'closestCompnent'
    """
    sel = mc.ls(sl=True, l=True, type='transform')

    try:
        src, dst = sel[0], sel[1]
        src_sc, src_inf, _, _ = get_skin_related_val(src)
        src_map = mc.polyUVSet(src, q=True, cuv=True)[0]

        # Get value to be used for binding option.
        max_inf = mc.getAttr(src_sc + '.maxInfluences')
        normalize_weights = mc.getAttr(src_sc + '.normalizeWeights')
        maintain_max_inf = mc.getAttr(src_sc + '.maintainMaxInfluences')

        # Bind skin
        mc.skinCluster(dst, src_inf, tsb=True, mi=max_inf,
                       omi=maintain_max_inf, nw=normalize_weights)

        # Copy weights
        dst_sc, _, _, _ = get_skin_related_val(dst)
        influence_association = ['label', 'oneToOne', 'name', 'closestJoint']
        if copymode == 'uv':
            # Only uv copymode uses another flag for copySkinWeights cmd.
            surface_association = 'closestPoint'
            dst_map = mc.polyUVSet(dst, q=True, cuv=True)[0]
            mc.copySkinWeights(ss=src_sc, ds=dst_sc, nm=True,
                   sa=surface_association, uvSpace = [src_map, dst_map],
                   ia=influence_association)
        else:
            surface_association = copymode
            mc.copySkinWeights(ss=src_sc, ds=dst_sc, nm=True,
                               sa=surface_association,
                               ia=influence_association)

        mc.select(src, dst, r=True)

    except:
        om2.MGlobal.displayError('Please select valid two objects (source, distination).')
        return