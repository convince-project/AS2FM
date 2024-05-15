# Build documentation

Before you can build the documentation, you need to install the required packages as described above, since also the code API documentation of those packages is built.

```
cd <path-to-convince_toolchain>/docs
pip install -e mc_toolchain_jani_common
pip install -e scxml_converter
pip install -r requirements.txt
make html
```