import sys
import os

from tornado.gen import coroutine, Return

from method_call import call_api

#TODO(DB): update collers to expect future
@coroutine
def load_methods():
    """
        Loads the list of all methods
    """
    try:
        r = yield call_api(method="flickr.reflection.getMethods")
    except Exception as e:
        raise e

    raise Return(r["methods"]["method"])

__perms__ = {0: 'none', '1': 'read', '2': 'write', '3': 'delete'}


#TODO(DB): update collers to expect future
@coroutine
def methods_info():
    methods = {}
    for m in load_methods():
        try:
            info = yield call_api(method="flickr.reflection.getMethodInfo", method_name=m)
        except Exception as e:
            raise e

        info.pop("stat")
        method = info.pop("method")
        method["requiredperms"] = __perms__[method["requiredperms"]]
        method["needslogin"] = bool(method.pop("needslogin"))
        method["needssigning"] = bool(method.pop("needssigning"))
        info.update(method)
        info["arguments"] = info["arguments"]["argument"]
        info["errors"] = info["errors"]["error"]
        methods[m] = info
    raise Return(methods)


def write_reflection(path, template, methods=None):
    if methods is None:
        methods = methods_info()
    with open(template, "r") as t:
        templ = t.read()

    prefix = ""
    new_templ = ""
    tab = "    "
    templ = templ % str(methods)
    for c in templ:
        if c == '{':
            new_templ += '{\n' + prefix
            prefix += tab
        elif c == '}':
            new_templ += '\n' + prefix + '}\n' + prefix
            prefix = prefix[:-len(tab)]
        else:
            new_templ += c

    with open(path, "w") as f:
        f.write(new_templ)


def write_doc(output_path, exclude=["flickr_keys", "methods"]):
    import flickr_api
    exclude.append("__init__")
    modules = ['flickr_api']
    dir = os.path.dirname(flickr_api.__file__)
    modules += [
        "flickr_api." + f[:-3]
            for f in os.listdir(dir)
            if f.endswith(".py") and f[:-3] not in exclude]
    sys.path.insert(0, dir + "../")
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    os.chdir(output_path)
    for m in modules:
        os.system("pydoc -w " + m)
