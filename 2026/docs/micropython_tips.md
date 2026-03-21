# MicroPython Tips :snake:

Table of Contents
<!-- @import "[TOC]" {cmd="toc" depthFrom=2 depthTo=6 orderedList=true} -->

<!-- code_chunk_output -->

1. [MicroPython does not support all Python modules/libraries :warning:](#micropython-does-not-support-all-python-moduleslibraries-warning)
2. [MicroPython is not 100% as Python :warning:](#micropython-is-not-100-as-python-warning)
3. [Detecting if you are on Python (x86 host) or MicroPython (mcu)](#detecting-if-you-are-on-python-x86-host-or-micropython-mcu)
4. [Loading MicroPython & Python modules with the same name](#loading-micropython-python-modules-with-the-same-name)
5. [Speed up your boot time](#speed-up-your-boot-time)
6. [Improving performances (profiling)](#improving-performances-profiling)

<!-- /code_chunk_output -->

## MicroPython does not support all Python modules/libraries :warning:

MicroPython is very cool... but it does not mean all Python modules/libraries are available on MicroPython! For the moment, only most important ones are available.

Please start reading [MicroPython libraries](https://docs.micropython.org/en/latest/library/index.html) where you will find all already available - sometimes partly - MicroPython libraries.

For instance:
* In MicroPython, the ```gc```, ```sys```, ```time```... are there but **only partly**, so caution when using them!
* Some famous libraries like [NumPy](https://numpy.org/), are not available... but some port are in progress like [ulab - the numpy-like](https://micropython-ulab.readthedocs.io/en/latest/ulab-intro.html) so if you need them, you will need to get these ports *by yourself*!

## MicroPython is not 100% as Python :warning:

MicroPython does not implement all Python 3.x features but only some, at least for the moment.

Moreover, there are sometimes "behavior differences" between the two implementations! For instance, the [Special method ```__del__``` is not implemented for user-defined classes](https://docs.micropython.org/en/latest/genrst/core_language.html#special-method-del-not-implemented-for-user-defined-classes) or the [Function objects do not have the ```__module__``` attribute](https://docs.micropython.org/en/latest/genrst/core_language.html#function-objects-do-not-have-the-module-attribute)...

So before implementing your MicroPython wonderful big library, please read carefully [MicroPython differences from CPython](https://docs.micropython.org/en/latest/genrst/index.html).

## Detecting if you are on Python (x86 host) or MicroPython (mcu)

Both Python & MicroPython offer ```sys.implementation.name``` that is useful to know if you are executing your Python code on a x86 host or on a mcu.

```python
import sys
if sys.implementation.name == 'cpython':
    SIMULATOR = True
else:
    SIMULATOR = False
```

Related documentations:
* [MicroPython sys.implementation](https://docs.micropython.org/en/latest/library/sys.html#sys.implementation)
* [Python sys.implementation](https://docs.python.org/3/library/sys.html#sys.implementation)

> :heavy_plus_sign: It is of course possible to test the MicroPython implementation name (```sys.implementation.name == 'micropython'```) and/or the MicroPython implementation version (```sys.implementation.version```)...


## Loading MicroPython & Python modules with the same name

Imagine you have two modules named ```mymodule``` and ```mymodule_simulator```, implementing the same functionnalities but differently for both MicroPython and Python. Then you can import the ```mymodule_simulator``` with the name ```mymodule``` thanks to ```as mymodule```.

```python
if SIMULATOR: # or if sys.implementation.name == 'cpython':
    import mymodule_simulator as mymodule # here the 'as' is important
else:
    import mymodule

f = mymodule.MyClass()  # same syntax for both mymodule & mymodule_simulator
a = f.get_something()
...
```

## Speed up your boot time

To speed up the boot time without modifying your source code, you can *preprocess* your python files with the command:
```shell
$> cd your_micropython_directory
$> mpy-cross mymodule.py
```
A new file named ```mymodule.mpy``` is created.

> :warning: Do not forget to replace in your target file system the old ```mymodule.py``` by the new ```mymodule.mpy```

Related documentation: [MicroPython .mpy files](https://docs.micropython.org/en/latest/reference/mpyfiles.html)

## Improving performances (profiling)

Please read the nice article named [Maximising MicroPython speed](https://docs.micropython.org/en/latest/reference/speed_python.html) explaining many tips for profiling and speeding up your code.

We confirm that ```bytearray()```, [Caching object references](https://docs.micropython.org/en/latest/reference/speed_python.html#caching-object-references), ```@micropython.native```, ```@micropython.viper``` work like a charm :smile:.

For instance, to measure the performance with ```@timed_function```, do the followings:
```python
def timed_function(f, *args, **kwargs):
    myname = str(f).split(' ')[1]
    def new_func(*args, **kwargs):
        t = time.ticks_us()
        result = f(*args, **kwargs)
        delta = time.ticks_diff(time.ticks_us(), t)
        print('Function {} Time = {:6.3f}ms'.format(myname, delta/1000))
        return result
    return new_func

...
a_lot = 1000
...

@timed_function
def my_function_to_profile(param1, param2):
    total = 0.0
    for i in range(a_lot):
        total += (param1 / param2)
    return total

my_function_to_profile(5, 10)
```

