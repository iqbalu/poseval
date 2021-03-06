import numpy as np
import json
import os
import sys

import eval_helpers
from eval_helpers import Joint
import motmetrics as mm


def computeMetrics(gtFramesAll, motAll):

    assert(len(gtFramesAll) == len(motAll))

    nJoints = Joint().count
    seqidxs = []
    for imgidx in range(len(gtFramesAll)):
        seqidxs += [gtFramesAll[imgidx]["seq_id"]]
    seqidxs = np.array(seqidxs)

    seqidxsUniq = np.unique(seqidxs)

    # intermediate metrics
    metricsMidNames = ['num_misses', 'num_switches', 'num_false_positives', 'num_objects', 'num_detections']

    # final metrics computed from intermediate metrics
    metricsFinNames = ['mota','motp','pre','rec']

    # initialize intermediate metrics
    metricsMidAll = {}
    for name in metricsMidNames:
        metricsMidAll[name] = np.zeros([1,nJoints])
    metricsMidAll['sumD'] = np.zeros([1,nJoints])

    # initialize final metrics
    metricsFinAll = {}
    for name in metricsFinNames:
        metricsFinAll[name] = np.zeros([1,nJoints+1])

    # create metrics
    mh = mm.metrics.create()

    imgidxfirst = 0
    # iterate over tracking sequences
    # seqidxsUniq = seqidxsUniq[:20]
    nSeq = len(seqidxsUniq)
    for si in range(nSeq):
        print "seqidx: %d/%d" % (si+1,nSeq)

        # init per-joint metrics accumulator
        accAll = {}
        for i in range(nJoints):
            accAll[i] = mm.MOTAccumulator(auto_id=True)

        # extract frames IDs for the sequence
        imgidxs = np.argwhere(seqidxs == seqidxsUniq[si])
        # DEBUG: remove the last frame of each sequence from evaluation due to buggy annotations
        print "DEBUG: remove last frame from eval until annotations are fixed"
        imgidxs = imgidxs[:-1].copy()
        # create an accumulator that will be updated during each frame
        # iterate over frames
        for j in range(len(imgidxs)):
            imgidx = imgidxs[j,0]
            # iterate over joints
            for i in range(nJoints):
                # GT tracking ID
                trackidxGT = motAll[imgidx][i]["trackidxGT"]
                # prediction tracking ID
                trackidxPr = motAll[imgidx][i]["trackidxPr"]
                # distance GT <-> pred part to compute MOT metrics
                # 'NaN' means force no match
                dist = motAll[imgidx][i]["dist"]
                # Call update once per frame
                accAll[i].update(
                    trackidxGT,                 # Ground truth objects in this frame
                    trackidxPr,                 # Detector hypotheses in this frame
                    dist                        # Distances from objects to hypotheses
                )

        # compute intermediate metrics per joint per sequence
        for i in range(nJoints):
            metricsMid = mh.compute(accAll[i], metrics=metricsMidNames, return_dataframe=False, name='acc')
            for name in metricsMidNames:
                metricsMidAll[name][0,i] += metricsMid[name]
            metricsMidAll['sumD'][0,i] += accAll[i].events['D'].sum()

    # compute final metrics per joint for all sequences
    for i in range(nJoints):
        metricsFinAll['mota'][0,i] = 100*(1. - (metricsMidAll['num_misses'][0,i] +
                                                metricsMidAll['num_switches'][0,i] +
                                                metricsMidAll['num_false_positives'][0,i]) /
                                                metricsMidAll['num_objects'][0,i])
        metricsFinAll['motp'][0,i] = 100*(1. - (metricsMidAll['sumD'][0,i] /
                                                metricsMidAll['num_detections'][0,i]))
        metricsFinAll['pre'][0,i]  = 100*(metricsMidAll['num_detections'][0,i] /
                                       (metricsMidAll['num_detections'][0,i] +
                                        metricsMidAll['num_false_positives'][0,i]))
        metricsFinAll['rec'][0,i]  = 100*(metricsMidAll['num_detections'][0,i] /
                                       metricsMidAll['num_objects'][0,i])

    # average metrics over all joints over all sequences
    metricsFinAll['mota'][0,nJoints] = metricsFinAll['mota'][0,:nJoints].mean()
    metricsFinAll['motp'][0,nJoints] = metricsFinAll['motp'][0,:nJoints].mean()
    metricsFinAll['pre'][0,nJoints]  = metricsFinAll['pre'] [0,:nJoints].mean()
    metricsFinAll['rec'][0,nJoints]  = metricsFinAll['rec'] [0,:nJoints].mean()

    return metricsFinAll


def evaluateTracking(gtFramesAll, prFramesAll):

    distThresh = 0.5
    # assign predicted poses to GT poses
    _, _, _, motAll = eval_helpers.assignGTmulti(gtFramesAll, prFramesAll, distThresh)

    # compute MOT metrics per part
    metricsAll = computeMetrics(gtFramesAll, motAll)

    return metricsAll
