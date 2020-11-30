# -*- coding: utf-8 -*-
from collections import defaultdict
import json
import math

PART_NAMES = ['tou', 'wan', 'xiong', 'yao', 'jiao']

ALL_EQUIPMENTS = {}
EQUPMENT_ID2INFO = {}

SKILL_NAME2ID = {}
SKILL_ID2NAME = {}

ACTIVATION_TO_SKILL = {}
ACTIVATION_ID2NAME = {}
ACTIVATION_NAME2ID = {}

ALL_GEMS = []
GEM_ID2INFO = {}

SKILL_TO_GEMS = defaultdict(list)
SKILL_MAX_GAIN = defaultdict(float)

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
                items.append([item["id"], skill_dict, item["hole"], item["type"], int(item["gender"]), item["maxDefense"]])
                EQUPMENT_ID2INFO[item["id"]] = [skill_dict, item["name_cn"]]
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
    gems = json.load(open("data/gems.json","r"))
    for gem in gems["data"]:
        skills = {}
        if gem["effect1"] in SKILL_NAME2ID:
            skill_id = SKILL_NAME2ID[gem["effect1"]]
            skills[skill_id] = gem["effect1_num"]
            SKILL_MAX_GAIN[skill_id] = max(SKILL_MAX_GAIN[skill_id], 1.0 * gem["effect1_num"] / gem["hole"])
        if gem["effect2"] in SKILL_NAME2ID:
            skill_id = SKILL_NAME2ID[gem["effect2"]]
            skills[skill_id] = gem["effect2_num"]
            SKILL_MAX_GAIN[skill_id] = max(SKILL_MAX_GAIN[skill_id], 1.0 * gem["effect2_num"] / gem["hole"])
        ALL_GEMS.append([gem["id"], skills, gem["hole"]])
        GEM_ID2INFO[gem["id"]] = [skills, gem["name_cn"]]

def load_activations():
    activations = json.load(open("data/activations.json","r"))
    for activtion in activations["data"]:
        ACTIVATION_ID2NAME[activtion["id"]] = activtion["skillFadong_cn"]
        ACTIVATION_NAME2ID[activtion["skillFadong_cn"]] = activtion["id"]


def init():
    load_equipments()
    load_skills()
    load_gems()
    load_activations()

def isDominate(la, lb):
    for a, b in zip(la, lb):
        if a < b:
            return False
    return True

"""
require_type: 0 melee 1 range
require_gender: 0 male 1 female
"""
def search_candidate(input_items, required_skills, require_type, require_gender):
    selected_items = []
    for item in input_items:
        # filter by type
        if require_type != -1 and item[3] != require_type:
            continue
        # filter by gender
        if item[4] != 0 and item[4] != require_gender + 1:
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
        selected_items.append([item[0], current_item, item[-1]])
    return selected_items


def prefilter_gem(required_skills):
    prefiltered_gems = []
    for gem in ALL_GEMS:
        is_useful = False
        gen_skill = [0] * len(required_skills)
        for i, skill in enumerate(required_skills):
            p = gem[1].get(skill, 0)
            if p > 0:
                is_useful = True
                gen_skill[i] = p
                break
        if is_useful:
            prefiltered_gems.append([gem[0], gen_skill, gem[2]])
    return prefiltered_gems


def is_greedy_possible(left_over_points, hole_counts, max_single_gain):
    # greedy prune
    total_holes = hole_counts[1] + 2* hole_counts[2] + 3 * hole_counts[3]
    for require, gain in zip(left_over_points, max_single_gain):
        if require <= 0:
            continue
        if gain < 1e-3:
            return False
        require_num = int(math.ceil(require / gain))
        total_holes -= require_num
        if total_holes < 0:
            return False
    return True


def search_gem(required_points, hole_counts, useful_gems, result, cache):
    is_done = True
    for v in required_points:
        if v > 0:
            is_done = False
            break
    if is_done:
        return True
    
    state = tuple([max(v, 0) for v in required_points] + hole_counts[1:])
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


def acc_skill_dict(skill_dict, new_skills):
    for k, v in new_skills.items():
        skill_dict[k] += v

        
def skill_dict2arr(skill_dict):
    skills = []
    for skill_id, skill_num in skill_dict.items():
        skills.append({
            "id": skill_id,
            "name_cn": SKILL_ID2NAME[skill_id],
            "num": skill_num
        })
        
    return sorted(skills, key=lambda x: -x["num"])
    

def generate_result(equipment_ids, gem_ids, stone_skills, total_def):
    result = {}
    total_skills = defaultdict(int)
    # equip result
    for equip_id, part in zip(equipment_ids, PART_NAMES):
        equip_info = EQUPMENT_ID2INFO[equip_id]
        acc_skill_dict(total_skills, equip_info[0])
        result[part] = {
            "id": equip_id,
            "name_cn": equip_info[1],
            "skills": skill_dict2arr(equip_info[0]),
        }
        
    # charm result
    acc_skill_dict(total_skills, stone_skills)
    result["charm"] = skill_dict2arr(stone_skills)
    
    # decoration result
    decoration_skills = defaultdict(int)
    gem_count = defaultdict(int)
    for gem_id in gem_ids:
        gem_count[gem_id] += 1
    jewels = []
    for gid, count in gem_count.items():
        gem_info = GEM_ID2INFO[gid]
        for i in range(count):
            acc_skill_dict(decoration_skills, gem_info[0])
        jewels.append({
            "id": gid,
            "name_cn": gem_info[1],
            "num": count,
        })
    result["decoration"] = {
        "jewels": jewels,
        "skills": skill_dict2arr(decoration_skills)
    }
    acc_skill_dict(total_skills, decoration_skills)
    
    # overall skills
    result["skills"] = skill_dict2arr(total_skills)
    
    # total defense used for sort
    result["total_def"] = total_def
    
    return result



def add_equip(left_over_points, hole_counts, equipment):
    for i in range(len(left_over_points)):
        left_over_points[i] -= equipment[1][i]
    hole_counts[equipment[1][-1]] += 1


def remove_equip(left_over_points, hole_counts, equipment):
    for i in range(len(left_over_points)):
        left_over_points[i] += equipment[1][i]
    hole_counts[equipment[1][-1]] -= 1


"""
Test request
{
  "skillEffect": [
    "5fb0c2e0d8c2f51f1bb39dc9",
    "5fb0c2e0d8c2f51f1bb39d9d",
    "5fb0c2e0d8c2f51f1bb39e5a",
    "5fb0c2e0d8c2f51f1bb39dae",
    "5fb0c2e0d8c2f51f1bb39e31"
  ],
  "stone_skills": [
      {
          "skillId": "5f87e09412c40c0c5bcfe760",
          "skillNum": 6
      }
  ],
  "hushiHole": 3,
  "weaponHole": 1,
  "type": 1,
  "gender": 0,
}
"""
def search_equipment(request_dict):
    required_activated_skills = request_dict["skillEffect"]
    stone_skills = {}
    for stone in request_dict["stone_skills"]:
        stone_skills[stone["skillId"]] = stone["skillNum"]
    stone_hole = request_dict["hushiHole"]
    weapon_hole = request_dict["weaponHole"]
    require_type = request_dict["type"]
    require_gender = request_dict["gender"]
    
    required_point_dict = defaultdict(int)
    for activated_skill in required_activated_skills:
        activated_skill_name = ACTIVATION_ID2NAME[activated_skill]
        required_point_dict[ACTIVATION_TO_SKILL[activated_skill_name][0]] += ACTIVATION_TO_SKILL[activated_skill_name][1]

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
        if key in id2dim:
            stone_points[id2dim[key]] = stone_skills[key]


    tou_equips = sorted(search_candidate(ALL_EQUIPMENTS["tou"], required_skills, -1, require_gender), key=lambda x: -x[-1])
    wan_equips = sorted(search_candidate(ALL_EQUIPMENTS["wan"], required_skills, require_type, require_gender), key=lambda x: -x[-1])
    xiong_equips = sorted(search_candidate(ALL_EQUIPMENTS["xiong"], required_skills, require_type, require_gender), key=lambda x: -x[-1])
    yao_equips = sorted(search_candidate(ALL_EQUIPMENTS["yao"], required_skills, require_type, require_gender), key=lambda x: -x[-1])
    jiao_equips = sorted(search_candidate(ALL_EQUIPMENTS["jiao"], required_skills, require_type, require_gender), key=lambda x: -x[-1])

    prefilered_gems = sorted(prefilter_gem(required_skills), key=lambda x: -x[-1])
    max_single_gain = [SKILL_MAX_GAIN[s] for s in required_skills]

    # hole counts
    hole_counts = [0] * 4
    hole_counts[weapon_hole] += 1
    hole_counts[stone_hole] += 1

    # loeft over skill points
    left_over_points = required_points[:]
    for i in range(len(left_over_points)):
        left_over_points[i] -= stone_points[i]

    results = []
    for tou in tou_equips:
        add_equip(left_over_points, hole_counts, tou)
        for wan in wan_equips:
            add_equip(left_over_points, hole_counts, wan)
            for xiong in xiong_equips:
                add_equip(left_over_points, hole_counts, xiong)
                for yao in yao_equips:
                    add_equip(left_over_points, hole_counts, yao)
                    for jiao in jiao_equips:
                        add_equip(left_over_points, hole_counts, jiao)
                        if is_greedy_possible([max(v, 0) for v in left_over_points], hole_counts, max_single_gain):
                            cahce = {}
                            result_gems = []
                            temp_points = left_over_points[:]
                            temp_holes = hole_counts[:]
                            # cache for DP
                            search_result = search_gem(temp_points, temp_holes, prefilered_gems, result_gems, cahce)
                            if search_result:
                                equpment_ids = [tou[0], wan[0], xiong[0], yao[0], jiao[0]]
                                total_def = sum([tou[-1], wan[-1], xiong[-1], yao[-1], jiao[-1]])
                                results.append(generate_result(equpment_ids, result_gems, stone_skills, total_def))
                                if len(results) >= MAX_SET:
                                    return {"results": sorted(results, key=lambda x: -x["total_def"])}
                        remove_equip(left_over_points, hole_counts, jiao)
                    remove_equip(left_over_points, hole_counts, yao)
                remove_equip(left_over_points, hole_counts, xiong)
            remove_equip(left_over_points, hole_counts, wan)
        remove_equip(left_over_points, hole_counts, tou)
    return {"results": sorted(results, key=lambda x: -x["total_def"])}
