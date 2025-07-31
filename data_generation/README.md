# Generate Synthetic Dataset



## Quick Start

To generate a dataset based on the 30 simulated people, with the default of 14 days per person, run command:
```
python -m data_generation.generate_dataset
```

### Notes about the script: 

- Insulin and CHO has default unit of grams or U _per sample time_, which is why we multiply them by 5 in this dataset
- In `simglucose/params/Quest.csv`, we have:
  - CR: Carb ratio, in g/U
  - CF: Correction factor (or Insulin Sensitivity Factor), in mg/dL/U
  - TDI: Total daily insulin, in U
- In this repo, we have significantly increased the std of the generated meal sizes, that originally have very similar sizes for all meals. This is set in `simglucose/simulation/scenario_gen.py`, in function `create_scenario`, variables `amount_sigma`. 
- We have used the basal-bolus controller


## Patient Params

Patient params are set in `simglucose/params/`.



