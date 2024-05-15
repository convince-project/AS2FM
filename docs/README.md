# Build documentation

Before you can build the documentation, you need to install the required packages as described above, since also the code API documentation of those packages is built.

```
pip install ../mc_toolchain_jani_common
pip install ../scxml_converter
pip install ../jani_generator
pip install -r requirements.txt
make html
```