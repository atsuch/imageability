#!/usr/bin/env python

# Doit tasks to set files according to BIDS format

import os.path as op
import pandas as pd
import sys
import json
import glob

from doit.cmd_base import ModuleTaskLoader
from doit.doit_cmd import DoitMain
from doit.task import clean_targets
from doit.action import CmdAction
from doit.tools import create_folder, run_once

# List project and raw data (dicom) directories
imaging_dir = "/home/ami/Documents/Work/imaging"
study_dir = "%s/ds001/" % imaging_dir
dicom_dir = "%s/RAW_All/dicom/" % imaging_dir
nifti_dir = "%s/RAW_All/nifti/ds001/" % imaging_dir

# File with subject numbers
participants_info = "%s/participants.tsv" % study_dir
participants_df = pd.read_csv(participants_info, sep="\t")
participants = participants_df.subject


def replace_all(text, dic):
    for i, j in dic.items():
        text = text.replace(i, j)
    return text


def get_path_dict(s):
    """Get common subject-specific paths used by the tasks."""
    path_dict = {}
    path_dict['dicom'] = glob.glob("%s%s*" % (dicom_dir, s))[0]
    path_dict['nifti'] = op.join(nifti_dir, "sub-%s" % s)

    return path_dict


def get_nifti_names(s, scan_key):
    """
    Return a dict containing lists of RAW nifti filenames and bids
    formatted nifti names for the subject using the scan_key
    """
    name_dict = {}
    scaninfo_txt = "%s/scaninfo.txt" % get_path_dict(s)["nifti"]
    scaninfo = pd.read_csv(scaninfo_txt, header=None, sep='\s*')
    scaninfo.columns = ["series", "protocol", "check", "x", "y", "z", "t", "dcm"]
    for idx, row in scaninfo.iterrows():
        for key, d in scan_key.items():
            if d["protocol"] == row.protocol and d["timepoints"] == row.t:
                d["count"] = d.get("count", 0) + 1
                for raw_nifti, bids in zip(d["raw_nifti_name"], d["bids_name"]):
                    repls = {"(sub)": "%s" % s,
                             "(prot)": "%s" % row.protocol,
                             "(series)": "%s" % row.series,
                             "(run)": "run-%02d" % d["count"]}
                    raw_name = replace_all(raw_nifti, repls)
                    target = replace_all(bids, repls)
                    name_dict[raw_name] = target
    return name_dict


def get_scan_info(subject):
    """ Returns a task to get scan info for the subject"""
    paths = get_path_dict(subject)
    src_dir = paths['dicom']
    out_dir = paths['nifti']
    out_file = "%s/scaninfo.txt" % out_dir
    return {
        'basename': 'get_scan_info',
        'name': subject,
        'doc': 'Use unpacksdcmdir to get scan info',
        'actions': [(create_folder, [out_dir]),
                    "unpacksdcmdir -src %s -targ %s -scanonly %s" %
                    (src_dir, out_dir, out_file)],
        'targets': [out_file],
        'uptodate': [run_once]
    }


def dicom2nifti(subject):
    """ Returns a task to convert dicom to nifti/json"""
    paths = get_path_dict(subject)
    src_dir = paths['dicom']
    out_dir = paths['nifti']
    return {
        'basename': 'dicom2nifti',
        'name': subject,
        'doc': 'Use dcm2niix to convert dicom to nifti',
        'actions': [(create_folder, [out_dir]),
                    "dcm2niix -b y -z y -f sub-%s_%%p%%s -o '%s' %s" %
                    (subject, out_dir, src_dir)],
        'uptodate': [run_once]
        }



def generate_all_tasks():

    for subj in participants:
        yield get_scan_info(subj)
        yield dicom2nifti(subj)

# This is just like calling doit from command line, except it can be
# called as a function
def doit(doit_args=[]):
    return DoitMain(ModuleTaskLoader(
        {'task_all': generate_all_tasks})).run(doit_args)

# Running from the commandline
if __name__ == "__main__":
    sys.exit(doit(sys.argv[1:]))
