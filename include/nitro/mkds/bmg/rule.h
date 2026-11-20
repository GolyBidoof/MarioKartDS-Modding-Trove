/* rule.h — message ids for Scene/MenuDL_us_arc/rule.bmg. SPDX-License-Identifier: MIT */
#pragma once

typedef enum {
    MKDS_BMG_RULE_CLASS = 0,
    MKDS_BMG_RULE_CPU_KART = 1,
    MKDS_BMG_RULE_COURSE = 2,
    MKDS_BMG_RULE_RULES = 3,
    MKDS_BMG_RULE_TEAM = 4,
} MkdsBmgRuleLabelMessage;

typedef enum {
    MKDS_BMG_RULE_ENGINE_50CC = 5,
    MKDS_BMG_RULE_ENGINE_100CC = 6,
    MKDS_BMG_RULE_ENGINE_150CC = 7,
    MKDS_BMG_RULE_ENGINE_MIRROR = 8,
} MkdsBmgRuleEngineMessage;

typedef enum {
    MKDS_BMG_RULE_ON = 9,
    MKDS_BMG_RULE_OFF = 10,
} MkdsBmgRuleToggleMessage;

typedef enum {
    MKDS_BMG_RULE_CPU_EASY = 11,
    MKDS_BMG_RULE_CPU_NORMAL = 12,
    MKDS_BMG_RULE_CPU_HARD = 13,
} MkdsBmgRuleCpuMessage;

typedef enum {
    MKDS_BMG_RULE_RULE_IN_ORDER = 14,
    MKDS_BMG_RULE_RULE_RANDOM = 15,
    MKDS_BMG_RULE_RULE_CHOOSE = 16,
} MkdsBmgRuleOrderMessage;

typedef enum {
    MKDS_BMG_RULE_WIN_S = 17,
    MKDS_BMG_RULE_RACE_S = 18,
    MKDS_BMG_RULE_FREE = 19,
    MKDS_BMG_RULE_SETTING_GAME_RULES = 20,
    MKDS_BMG_RULE_USE_TO_CHOOSE_TEAMS = 21,
    MKDS_BMG_RULE_WIN_S_2 = 22,
    MKDS_BMG_RULE_RACE_S_2 = 23,
} MkdsBmgRuleMiscMessage;

#define MKDS_BMG_RULE_COUNT 24u
