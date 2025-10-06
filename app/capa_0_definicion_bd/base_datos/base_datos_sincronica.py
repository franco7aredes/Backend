"""Módulo sincrónico de base de datos eliminado tras migración completa a async.

Se mantiene el archivo para evitar import errors si existiera alguna referencia residual,
pero no expone API. Si aparece alguna dependencia, hay que migrarla a async.
"""
