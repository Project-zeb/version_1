def create_app(*args, **kwargs):
    from disaster_api.app import create_app as _create_app

    return _create_app(*args, **kwargs)


__all__ = ["create_app"]
