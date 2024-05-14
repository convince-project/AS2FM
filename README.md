# Model Checking Toolchain Components - `mc-toolchain-jani`

The detailed documentation in a tutorial style including the API documentation can be found in `docs` after building it (see last section of this README). This README is only a quick start guide with the rudimentary steps to execute the tools.

## jani_generator: Convert CONVINCE Jani to plain Jani

### Installation using pip

```bash
cd <path-to-convince_toolchain>/jani_generator
python3 -m pip install -e .
```

### Running it

After it has been installed:

```bash
convince_to_plain_jani --convince_jani path_to_convince_file.jani --output output_plain_file.jani
```

### Working example

The first working example is a Markov Chain describing the robot driving around in a room. The robot moves forward in 50% of the cases and rotates in 50% of the cases.

The CONVINCE Jani model can be found [here](jani_generator/test/_test_data/first-model-mc-version.jani), and can be converted following the instructions above.

Once the conversion to plain Jani is done, it can be model checked in The Modest Toolset using the following commands for Statistical Model Checking or full state space model checking, respectively:

```bash
modest simulate <path_to_plain_jani_model.jani> -E "" --props "go-to-position" --independent --conf 0.95 --width 0.01 --threads 5 --batch-size 100 --max-run-length-as-end --max-run-length <max-n-steps>
```

#### Modest / Full state space

```bash
modest mcsta test/_test_data/battery_example/demo_manual.jani -E "" --props battery_depleted
```

#### Modest / Statistical Model Checking

```bash
modest modes main.jani -E "" --props battery_depleted -R Uniform
```

#### Modest / Statistical Model Checking with writing traces to csv

```bash
modest modes main.jani -E "" --props battery_depleted -R Uniform -T -TF log.csv
```

## Example converting ScXML to Jani

```bash
scxml_to_jani
TODO
```

## Build documentation

Before you can build the documentation, you need to install the required packages as described above, since also the code API documentation of those packages is built.

```
cd <path-to-convince_toolchain>/docs
pip install -e convince_mt_tc_common
pip install -e scxml_converter
pip install -r requirements.txt
make html
```

## Further Information

### Contribution Guidelines

See [Contributing](./CONTRIBUTING.md).

### Feedback

Feedback is highly appreciated. Please open issues on new ideas, bugs, etc. here at [mc-toolchain-jani/issues](https://github.com/convince-project/mc-toolchain-jani/issues) or reach out to the maintainers.

### License

mc-toolchain-jani comes under the Apache-2.0 license, see [LICENSE](./LICENSE).