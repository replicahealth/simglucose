# Generate Synthetic Dataset



## Quick Start

To generate a dataset based on the 30 simulated people, with the default of 14 days per person, run command:
```
python -m data_generation.generate_dataset
```


## Adjustments

Adjust `generate_dataset.py` to generate various datasets:
- `N_DAYS`: Number of days to generate per subject
- `COMPUTE_THERAPY_SETTINGS`: Whether to compute the therapy settings for the subject based on the total daily doses, using fixed rules (1800 for ISF and 500 for CR). If False, the therapy settings in `simglucose/params/Quest.csv` will be used.
- `CONTROLLER`: Which controller to use
- `patient_ids`: Which patients to include. Must be all or a subset of the 30 patients available.


### Notes about the script: 

- Insulin and CHO has default unit of grams or U _per sample time_, which is why we multiply them by 5 in this dataset
- In this repo, we have significantly increased the std of the generated meal sizes, that originally have very similar sizes for all meals. This is set in `simglucose/simulation/scenario_gen.py`, in function `create_scenario`, variables `amount_sigma`. 


## Patient Params and Therapy Settings

Patient params are set in `simglucose/params/`.

In `simglucose/params/Quest.csv`, we have:
- CR: Carb ratio, in g/U
- CF: Correction factor (or Insulin Sensitivity Factor), in mg/dL/U
- TDI: Total daily insulin, in U


