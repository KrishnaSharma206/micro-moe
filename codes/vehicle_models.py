"""
Car-following model sets for the model-comparison study.

Each model set defines the SUMO vehicle types for the two driver classes:
  human : the human-driven vehicle type (id "human")
  AV    : the automated vehicle type (id "AV")

Set            human model   AV model   notes
-------------  ------------  ---------  --------------------------------------
krauss         Krauss        Krauss     Original setup. Parameters from Sadid &
                                        Antoniou (2023), IET Intell. Transp.
                                        Syst., Table 4: human = Level 0,
                                        AV = Level 5.
idm_acc        IDM           ACC        Standard "human = IDM, AV = ACC" pair.
eidm_acc       EIDM          ACC        As above, but the human model is SUMO's
                                        Extended IDM (adds driver imperfection).
idm_cacc       IDM           CACC       Cooperative ACC. EXPERIMENTAL -- see below.

Design choices (so the comparison isolates the CONTROL LAW, not hardware):
  * For the IDM/EIDM/ACC/CACC sets, human and AV share the same physical
    limits: accel 2.6, decel 4.5, minGap 2.5, maxSpeed 16.6. These equal SUMO's
    default vehicle values and the Level-0 row of Sadid & Antoniou (2023).
  * The only difference between human and AV is the model and the desired time
    headway `tau`. AV headway defaults to 1.3 s, the value used for ACC/CACC
    vehicles in Syed & Hasan (2023), arXiv:2311.06267 (after Rahman et al.,
    2021, Transp. Res. C 128). Override with --av-tau to run a sensitivity
    study (e.g. 0.8, 1.0, 1.3). NOTE: a 1.3 s headway is LONGER than the human
    1.0 s, so ACC may well do worse than humans at signals. That is a finding
    to report, not a bug -- but it is a modelling assumption, so test it.
  * ACC/CACC controller gains are left at SUMO's defaults. SUMO's ACC and CACC
    follow Milanes & Shladover (2014, Transp. Res. C 48) and Xiao, Wang & van
    Arem (2017). Gain values in the literature are inconsistent (Syed & Hasan
    2023 compare three sets), so overriding them without calibration data would
    be guesswork.
  * CACC caveats from the SUMO docs and from Syed & Hasan (2023): SUMO's CACC
    is "primarily intended for use in specific traffic situations", is known to
    collide at the default 1 s step, and gave highly unstable results in their
    freeway study. A CACC vehicle only uses cooperative mode behind another
    CACC vehicle; behind a human it behaves like ACC. Treat idm_cacc as an
    exploratory upper bound and check its collision and unfinished-trip counts.
  * A more conservative near-term-CAV Krauss alternative (not run by default) is
    Amini et al. (2023), arXiv:2301.11083, Table 3: HDV minGap 2.5, accel 2.6,
    decel 4.5, sigma 0.5, tau 1.0, lcAssertive 1.3; CAV minGap 1.5, accel 3.5,
    decel 4.5, sigma 0, tau 0.9, lcAssertive 0.7.
"""

SIM_PHYSICS = dict(
    vClass="passenger", accel="2.6", decel="4.5", minGap="2.5", maxSpeed="16.6",
)

# model_set -> (human car-following model, AV car-following model)
MODEL_SETS = {
    "krauss":   ("Krauss", "Krauss"),
    "idm_acc":  ("IDM",    "ACC"),
    "eidm_acc": ("EIDM",   "ACC"),
    "idm_cacc": ("IDM",    "CACC"),
}

DEFAULT_AV_TAU = {
    "krauss": 0.6,
    "idm_acc": 1.3,
    "eidm_acc": 1.3,
    "idm_cacc": 1.3,
}


def get_vtypes(model_set, av_tau=None):
    """Returns (human_vtype, av_vtype, effective_av_tau) as attribute dicts."""
    if model_set not in MODEL_SETS:
        raise ValueError(f"unknown model set {model_set!r}; choose from {list(MODEL_SETS)}")
    human_cf, av_cf = MODEL_SETS[model_set]
    tau = DEFAULT_AV_TAU[model_set] if av_tau is None else av_tau

    if model_set == "krauss":
        human = dict(id="human", carFollowModel="Krauss", sigma="0.5", tau="1.0",
                     color="0.6,0.6,0.6", **SIM_PHYSICS)
        av = dict(SIM_PHYSICS, id="AV", carFollowModel="Krauss", sigma="0.0",
                  tau=f"{tau:g}", accel="3.8", minGap="0.5", color="0,0.8,0")
    else:
        human = dict(id="human", carFollowModel=human_cf, tau="1.0",
                     color="0.6,0.6,0.6", **SIM_PHYSICS)
        av = dict(id="AV", carFollowModel=av_cf, tau=f"{tau:g}",
                  color="0,0.8,0", **SIM_PHYSICS)
    return human, av, tau
