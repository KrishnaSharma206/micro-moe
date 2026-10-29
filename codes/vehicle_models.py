"""
Car-following model sets for the model-comparison study.

Each model set defines the SUMO vehicle types for the two driver classes:
  human : the human-driven vehicle type (id "human")
  AV    : the automated vehicle type (id "AV")

Set            human model   AV model
-------------------------------------
krauss         Krauss        Krauss   
idm_acc        IDM           ACC        
eidm_acc       EIDM          ACC        
                                        
idm_cacc       IDM           CACC      
"""

SIM_PHYSICS_PASSENGER = dict(vClass="passenger", accel="2.786", decel="7.424", minGap="2.377", maxSpeed="16.6", sigma="0.292", tau="1.001", speedFactor="1.193", speedDev="0.091", lcSpeedGain="0.887", lcKeepRight="0.835", lcAssertive="1.616")
SIM_PHYSICS_MOTORCYCLE = dict(vClass="motorcycle", accel="5.994", decel="9.848", minGap="2.506", maxSpeed="16.6", sigma="0.439", tau="1.038", speedFactor="1.073", speedDev="0.134", lcSpeedGain="1.0391", lcKeepRight="1.956", lcAssertive="1.057")
SIM_PHYSICS_TRUCK = dict(vClass="truck", accel="1.285", decel="3.820", minGap="2.136", maxSpeed="16.6", sigma="0.186", tau="1.775", speedFactor="1.043", speedDev="0.104", lcSpeedGain="0.985", lcKeepRight="1.696", lcAssertive="1.001")
SIM_PHYSICS_TRAILER = dict(vClass="trailer", accel="1.186", decel="4.013", minGap="2.181", maxSpeed="16.6", sigma="0.008", tau="3.471", speedFactor="0.866", speedDev="0.025", lcSpeedGain="0.967", lcKeepRight="1.977", lcAssertive="1.157")

HUMAN_CLASSES = {
    "human_passenger": SIM_PHYSICS_PASSENGER,
    "human_motorcycle": SIM_PHYSICS_MOTORCYCLE,
    "human_truck": SIM_PHYSICS_TRUCK,
    "human_trailer": SIM_PHYSICS_TRAILER,
}

MODEL_SETS = {
    "krauss":   ("Krauss", "Krauss"),
    "idm_acc":  ("IDM",    "ACC"),
    "eidm_acc": ("EIDM",   "ACC"),
    "idm_cacc": ("IDM",    "CACC"),
}

DEFAULT_AV_TAU = {
    "krauss": 0.6,
    "idm_acc": 1.5,   # Increased base to test conservative AV behavior
    "eidm_acc": 1.5,
    "idm_cacc": 1.5,
}

def get_vtypes(model_set, av_tau=None):
    """Returns (human_vtypes_dict, av_vtype, effective_av_tau)."""
    if model_set not in MODEL_SETS:
        raise ValueError(f"unknown model set {model_set!r}")
    human_cf, av_cf = MODEL_SETS[model_set]
    tau = DEFAULT_AV_TAU[model_set] if av_tau is None else av_tau

    human_vtypes = {}
    for type_id, physics in HUMAN_CLASSES.items():
        params = dict(physics)
        params["id"] = type_id
        params["carFollowModel"] = "Krauss" if human_cf == "Krauss" else human_cf
        human_vtypes[type_id] = params

    # AV uses passenger dynamics but with precise control and conservative lane changes
    av_physics = dict(SIM_PHYSICS_PASSENGER)
    av_physics.update({
        "id": "AV",
        "carFollowModel": "Krauss" if av_cf == "Krauss" else av_cf,
        "tau": f"{tau:g}",
        "sigma": "0.0",
        "color": "0,0.8,0",
        "lcAssertive": "0.7",  # Lower assertiveness = safer/conservative lane changing
        "lcSpeedGain": "0.5"   # Less likely to change lanes just for speed
    })
    
    if model_set == "krauss":
        av_physics.update({"accel": "3.8", "minGap": "0.5"})

    return human_vtypes, av_physics, tau
