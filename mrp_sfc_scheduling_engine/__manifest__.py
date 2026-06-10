# -*- coding: utf-8 -*-
# Copyright (c) Open Value All Rights Reserved

{
    'name': 'MRP SFC Scheduling Engine',
    'summary': 'Finite-capacity scheduling optimizer for Shop Floor Control',
    'description': """
MRP SFC Scheduling Engine
=========================

Adds a finite-capacity scheduling optimizer on top of MRP Shop Floor Control.

Where the base Shop Floor Control plans work orders at infinite capacity
(each operation simply starts when its predecessor finishes), this module
levels the load across work centers: it assigns every open work order a
conflict-free processing sequence and slot, respecting each work center's
finite capacity and working calendar.

The optimizer is a calendar-aware list-scheduling heuristic. The chosen
objective function selects the dispatching rule:

* Makespan: minimise the time to complete all orders (LPT rule)
* Tardiness: minimise lateness against order deadlines (EDD rule)
* Sum Completion: minimise the sum of order completion times (SPT rule)
* Length / WIP: minimise flow time / work in progress (release FIFO)

It writes the resulting schedule onto the Shop Floor Control planning layer
(date_planned_start_wo / date_planned_finished_wo) and rebuilds the capacity
load, reusing the existing Shop Floor Control infrastructure. The base
planner (button_plan) is left untouched; this engine is an additional
"Optimise" action.
""",
    'version': '19.0.1.0.0',
    'category': 'Manufacturing',
    'author': 'OpenValue',
    'website': 'www.openvalue.cloud',
    'support': 'info@openvalue.cloud',
    'license': 'OPL-1',
    'depends': [
        'mrp_shop_floor_control',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/mrp_scheduling_run_views.xml',
    ],
    'application': False,
    'installable': True,
    'auto_install': False,
}
