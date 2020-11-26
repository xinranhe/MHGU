# -*- coding: utf-8 -*-
from collections import defaultdict
import json
import math

PART_NAMES = ['tou', 'wan', 'xiong', 'yao', 'jiao']

ALL_EQUIPMENTS = {}
SKILL_NAME2ID = {}
SKILL_ID2NAME = {}
ACTIVATION_TO_SKILL = {}
ALL_GEMS = []

MAX_SET = 20

def load_equipments():
    equipments = json.load(open("data/equipment.json", "r"))
    for part in PART_NAMES:
        items = []
        for item in equipments["data"]:
            if item["buwei"] == part:
                skill_dict = {}
                for skill in item["skillArray"]:
                    skill_dict[skill["skillId"]] = skill.get("skillNum", 0)
                name = "%s (%s/%s)" % (item["name_cn"], item["name"], item["name_en"])
                items.append([name, skill_dict, item["hole"], item["type"], item["initDefense"], item["maxDefense"]])
        ALL_EQUIPMENTS[part] = items


def load_skills():
    skills = json.load(open("data/skill_activation.json", "r"))
    for item in skills["data"]:
        SKILL_NAME2ID[item["skillPointName_cn"]] = item["id"]
        SKILL_ID2NAME[item["id"]] = item["skillPointName_cn"]
        for activation in item["skillFadongArray"]:
            if int(activation["num"]) > 0:
                ACTIVATION_TO_SKILL[activation["skillFadong_cn"]] = (item["id"], int(activation["num"]))


def load_gems():
    gems = json.load(open("data/gems.json", "r"))
    for gem in gems["data"]:
        skills = {}
        if gem["effect1"] in SKILL_NAME2ID:
            skills[SKILL_NAME2ID[gem["effect1"]]] = gem["effect1_num"]
        if gem["effect2"] in SKILL_NAME2ID:
            skills[SKILL_NAME2ID[gem["effect2"]]] = gem["effect2_num"]
        ALL_GEMS.append([gem["name_cn"], skills, gem["hole"]]) 


def init():
    load_equipments()
    load_skills()
    load_gems()


def isDominate(la, lb):
    for a, b in zip(la, lb):
        if a < b:
            return False
    return True


def search_candidate(input_items, required_skills, require_type):
    selected_items = []
    for item in input_items:
        if require_type != -1 and item[-3] !=  require_type:
            continue
        current_item = []
        total = 0
        for s in required_skills:
            skill_num = item[1].get(s, 0)
            total += skill_num
            current_item.append(skill_num)
        current_item.append(item[2])

        if total == 0:
            continue

        is_dominated = False
        for sitem in selected_items:
            if isDominate(sitem[1], current_item):
                is_dominated = True
                break

        if is_dominated:
            continue

        selected_items = [sitem for sitem in selected_items if not isDominate(current_item, sitem[1])]
        selected_items.append([item[0], current_item, item[-2], item[-1]])
    return selected_items


def prefilter_gem(required_skills):
    prefiltered_gems = []
    for gem in ALL_GEMS:
            is_useful = False
            for skill in required_skills:
                if gem[1].get(skill, 0) > 0:
                    is_useful = True
                    break
            if is_useful:
                prefiltered_gems.append(gem)
    return prefiltered_gems


def prepare_gem_search(equipments, required_skills, required_points, stone_points, stone_hole, weapon_hole, prefilter_gems):
    hole_counts = [0] * 4 # holes for 1, 2, 3
    hole_counts[stone_hole] += 1
    hole_counts[weapon_hole] += 1
    
    left_over_points = required_points[:]
    num_skills = len(left_over_points)
    
    # count stone skill
    for i in range(num_skills):
        left_over_points[i] -= stone_points[i]
        
    for equip in equipments:
        hole_counts[equip[1][-1]] += 1
        for i in range(num_skills):
            left_over_points[i] -= equip[1][i]
    
    # new requirement
    new_required_skills = []
    new_required_points = []
    for i in range(num_skills):
        if left_over_points[i] > 0:
            new_required_skills.append(required_skills[i])
            new_required_points.append(left_over_points[i])
    
    # filter useful gems
    useful_gems = []
    max_single_gain = [0.0] * len(new_required_skills)
    for gem in prefilter_gems:
        is_useful = False
        gen_skill = [0] * len(new_required_skills)
        for i, skill in enumerate(new_required_skills):
            p = gem[1].get(skill, 0)
            if p > 0:
                is_useful = True
                gen_skill[i] = p
                max_single_gain[i] = max(max_single_gain[i], 1.0 * p / gem[2])
        if is_useful:
            useful_gems.append([gem[0], gen_skill, gem[2]])
    
    # greedy prune
    total_holes = hole_counts[1] + 2* hole_counts[2] + 3 * hole_counts[3]
    for require, gain in zip(new_required_points, max_single_gain):
        require_num = int(math.ceil(require / gain))
        total_holes -= require_num
        if total_holes < 0:
            return False, None, None, None, None
    
    return True, [max(v, 0) for v in left_over_points], hole_counts, new_required_points, useful_gems


def search_gem(required_points, hole_counts, useful_gems, result, cache):
    is_done = True
    for v in required_points:
        if v > 0:
            is_done = False
            break
    if is_done:
        return True
    
    state = tuple(required_points + hole_counts)
    if state in cache:
        return cache[state]
    
    for gem in useful_gems:
        is_useful = False
        for i, v in enumerate(gem[1]):
            if required_points[i] > 0 and v > 0:
                is_useful = True
                break
        if is_useful:
            for h in range(1, 4):
                if gem[2] <= h and hole_counts[h] > 0:
                    hole_counts[h] -= 1
                    hole_counts[h - gem[2]] += 1
                    
                    for i, v in enumerate(gem[1]):
                        required_points[i] -= v

                    result.append(gem[0])
                    cache[state] = search_gem(required_points, hole_counts, useful_gems, result, cache)
                    if cache[state]:
                        return True
                    result.pop()
                    for i, v in enumerate(gem[1]):
                        required_points[i] += v
                    
                    hole_counts[h] += 1
                    hole_counts[h - gem[2]] -= 1
    return False

def summarize_gems(gems):
    count = defaultdict(int)
    for gem in gems:
        count[gem] += 1
    results = []
    for gem in sorted(count.keys()):
        results.append("%s X %d" % (gem, count[gem]))
    return ", ".join(results)

"""
Request dict
{
  "required_activated_skills": [
    "洞悉+2",
    "弱点特效",
    "贯通弹・贯通箭UP",
    "超会心",
    "弹导强化"
  ],
  "stone_skills": {
    "痛击": 6
  },
  "stone_hole": 3,
  "weapon_hole": 1,
  "is_gunner": 1
}
""" 
def search_equipment(request_dict):
    required_activated_skills = request_dict["required_activated_skills"]
    stone_skills = request_dict["stone_skills"]
    stone_hole = request_dict["stone_hole"]
    weapon_hole = request_dict["weapon_hole"]
    is_gunner = request_dict["is_gunner"]

    required_point_dict = defaultdict(int)
    for activated_skill in required_activated_skills:
        required_point_dict[ACTIVATION_TO_SKILL[activated_skill][0]] += ACTIVATION_TO_SKILL[activated_skill][1]

    id2dim = {}
    required_skills = []
    for key in required_point_dict.keys():
        id2dim[key] = len(required_skills)
        required_skills.append(key)
        
    required_points = [0] * len(required_skills)
    stone_points = [0] * len(required_skills)
    for key in required_point_dict.keys():
        required_points[id2dim[key]] = required_point_dict[key]
    for key in stone_skills:
        stone_points[id2dim[SKILL_NAME2ID[key]]] = stone_skills[key]

    tou_equips = sorted(search_candidate(ALL_EQUIPMENTS["tou"], required_skills, -1), key=lambda x: -x[-1])
    wan_equips = sorted(search_candidate(ALL_EQUIPMENTS["wan"], required_skills, is_gunner), key=lambda x: -x[-1])
    xiong_equips = sorted(search_candidate(ALL_EQUIPMENTS["xiong"], required_skills, is_gunner), key=lambda x: -x[-1])
    yao_equips = sorted(search_candidate(ALL_EQUIPMENTS["yao"], required_skills, is_gunner), key=lambda x: -x[-1])
    jiao_equips = sorted(search_candidate(ALL_EQUIPMENTS["jiao"], required_skills, is_gunner), key=lambda x: -x[-1])

    prefilered_gems = prefilter_gem(required_skills)
    results = []
    for tou in tou_equips:
        for wan in wan_equips:
            for xiong in xiong_equips:
                for yao in yao_equips:
                    for jiao in jiao_equips:
                        equipments = [tou, wan, xiong, yao, jiao]
                        is_possible, left_over_points, hole_counts, new_required_points, useful_gems = prepare_gem_search(equipments, required_skills, required_points, stone_points, stone_hole, weapon_hole,prefilered_gems)
                        if is_possible:
                            result_gems = []
                            cahce = {}
                            useful_gems = sorted(useful_gems, key=lambda x: -x[2])
                            if search_gem(new_required_points, hole_counts, useful_gems, result_gems, cahce):
                                find_equipments = [e[0] for e in equipments]
                                results.append({
                                    "total_init_def": tou[-2]+wan[-2]+xiong[-2]+yao[-2]+jiao[-2],
                                    "total_def": tou[-1]+wan[-1]+xiong[-1]+yao[-1]+jiao[-1],
                                    "equipments": find_equipments,
                                    "gems": summarize_gems(result_gems)
                                })
                                if len(results) >= MAX_SET:
                                    return {"results": results}
    return {"results": results}
