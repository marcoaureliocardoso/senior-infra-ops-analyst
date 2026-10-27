"""Finite structural CI failure projection; never serialize exception text."""
import json


PHASES = frozenset({'NONE', 'PREPARE', 'VERIFY', 'CLEANUP'})
STAGES = frozenset('''NONE UNKNOWN_STAGE EXECUTOR_INIT CACHE_CREATE
PACKAGE_REFRESH PACKAGE_SNAPSHOT PACKAGE_HOLDS PACKAGE_METADATA PACKAGE_VERIFY
PACKAGE_UPGRADE_SIMULATE PACKAGE_DEPENDENCIES_SIMULATE
PACKAGE_UPGRADE_FREEZE PACKAGE_DEPENDENCIES_FREEZE
PACKAGE_UPGRADE_APPLY PACKAGE_DEPENDENCIES_APPLY
RUNTIME_BUILD_DOWNLOAD RUNTIME_BUILD_EXTRACT RUNTIME_BUILD_CONFIGURE
RUNTIME_BUILD_COMPILE RUNTIME_BUILD_BINARY RUNTIME_INSTALL RUNTIME_PUBLISH
NAMESPACE_FULL NAMESPACE_MINIMAL POLICY_SNAPSHOT POLICY_AUDIT POLICY_TEMPLATE
POLICY_LOAD POLICY_TRANSITION VERIFY_RUNTIME VERIFY_PROOF VERIFY_REAL_AUDIT
PUBLISH_PATH CLEANUP_POLICY CLEANUP_RUNTIME CLEANUP_CACHE CLEANUP_WORKSPACE'''.split())
ERRORS = frozenset('''NONE UNKNOWN_ERROR OS_ERROR INTERRUPTED CLEANUP_UNPROVEN
APT_SIMULATION_INVALID APT_SIMULATION_UNRECOGNIZED APT_SIMULATION_DRIFT APT_SIMULATION_AMBIGUOUS
CI_BOOTSTRAP_DEADLINE CI_COMMAND_SCOPE_REJECTED CI_COMMAND_BOUNDED_FAILURE CI_COMMAND_FAILED
CI_NAMESPACE_PROBE_BOUNDED_FAILURE CI_NAMESPACE_UNPROVEN CI_POLICY_STATE_UNPROVEN
CI_POLICY_EVIDENCE_MISSING CI_POLICY_EVIDENCE_REJECTED CI_POLICY_TEMPLATE_CHANGED
CI_POLICY_CHILD_UNPROVEN CI_POLICY_CLEANUP_FAILED CI_RUNTIME_IDENTITY_CHANGED
CI_REAL_AUDIT_UNPROVEN CI_PATH_PUBLICATION_REJECTED CI_WORKSPACE_IDENTITY_CHANGED
PACKAGE_STATE_UNPROVEN PACKAGE_HOLDS_UNPROVEN PACKAGE_HOLD_CHANGE_REJECTED
PACKAGE_PROPOSAL_BLOCKED PACKAGE_PROPOSAL_TOO_LARGE PACKAGE_CANDIDATE_UNSAFE
PACKAGE_PROPOSAL_DRIFT PACKAGE_STATE_CHANGED PACKAGE_PROVISIONING_DEADLINE
PACKAGE_OWNERSHIP_UNPROVEN PACKAGE_CACHE_UNSAFE PACKAGE_CACHE_TOO_LARGE
PACKAGE_ARCHIVE_UNPROVEN PACKAGE_ARCHIVE_UNAVAILABLE PACKAGE_CACHE_CHANGED
PACKAGE_POSTCONDITION_FAILED RUNTIME_SPEC_INVALID RUNTIME_PREFIX_COLLISION
RUNTIME_ARCHITECTURE_UNSUPPORTED RUNTIME_BINARY_CHANGED'''.split())
KEYS = frozenset({'phase', 'stage', 'error', 'cleanup', 'cleanupStage', 'cleanupError', 'aptRejection'})
APT_LINE_KINDS = frozenset('''INST_SUFFIX CONF_SUFFIX REMV_SUFFIX INST_OTHER CONF_OTHER
REMV_OTHER SUMMARY_VARIANT NOTICE WARNING HELD_CHANGE_HEADER HEADER OTHER'''.split())


def empty_diagnostics():
    return dict(phase='NONE', stage='NONE', error='NONE', cleanup='NOT_ATTEMPTED',
                cleanupStage='NONE', cleanupError='NONE', aptRejection=None)


def validate_apt_rejection(value):
    if value is None: return None
    if (type(value) is not dict or set(value) != {'kind', 'line', 'length'}
            or type(value['kind']) is not str or value['kind'] not in APT_LINE_KINDS
            or type(value['line']) is not int or not 1 <= value['line'] <= 4096
            or type(value['length']) is not int or not 1 <= value['length'] <= 524288):
        raise ValueError('CI_DIAGNOSTICS_INVALID')
    return value


def validate_diagnostics(value):
    if (type(value) is not dict or set(value) != KEYS
            or any(type(value[key]) is not str for key in KEYS - {'aptRejection'})):
        raise ValueError('CI_DIAGNOSTICS_INVALID')
    if (value['phase'] not in PHASES or value['stage'] not in STAGES or value['error'] not in ERRORS
            or value['cleanupStage'] not in STAGES or value['cleanupError'] not in ERRORS
            or value['cleanup'] not in ('NOT_ATTEMPTED', 'PASSED', 'FAILED')):
        raise ValueError('CI_DIAGNOSTICS_INVALID')
    if (value['error'] == 'NONE') != (value['phase'] == 'NONE' and value['stage'] == 'NONE'):
        raise ValueError('CI_DIAGNOSTICS_INVALID')
    if validate_apt_rejection(value['aptRejection']) is not None and value['error'] != 'APT_SIMULATION_UNRECOGNIZED':
        raise ValueError('CI_DIAGNOSTICS_INVALID')
    return value


def failure_stage(executor):
    stage = getattr(executor, 'stage', 'UNKNOWN_STAGE')
    return stage if type(stage) is str and stage in STAGES else 'UNKNOWN_STAGE'


def error_code(error):
    if isinstance(error, KeyboardInterrupt): return 'INTERRUPTED'
    if isinstance(error, OSError): return 'OS_ERROR'
    # Only exact built-in scalar args; never str/repr, chains or subclass properties.
    if type(error) is ValueError:
        if len(error.args) == 4 and apt_rejection(error) is not None:
            return 'APT_SIMULATION_UNRECOGNIZED'
        if len(error.args) == 1:
            code = error.args[0]
            if type(code) is str and code in ERRORS - {'NONE'}: return code
    return 'UNKNOWN_ERROR'


def apt_rejection(error):
    if (type(error) is ValueError and len(error.args) == 4
            and type(error.args[0]) is str and error.args[0] == 'APT_SIMULATION_UNRECOGNIZED'):
        value = dict(kind=error.args[1], line=error.args[2], length=error.args[3])
        try: return validate_apt_rejection(value)
        except ValueError: pass
    return None


def remember_failure(executor, phase, error):
    """Latch before any internal cleanup can replace the current stage."""
    if getattr(executor, 'primary_failure', None) is None:
        executor.primary_failure = dict(phase=phase, stage=failure_stage(executor), error=error_code(error),
                                        aptRejection=apt_rejection(error))


def record_failure(record, phase, error, executor=None):
    diag = record['diagnostics']
    if diag['error'] != 'NONE': return
    prior = getattr(executor, 'primary_failure', None)
    values = prior if type(prior) is dict else dict(phase=phase, stage=failure_stage(executor), error=error_code(error),
                                                 aptRejection=apt_rejection(error))
    candidate = {**diag, **values}
    validate_diagnostics(candidate)
    record['diagnostics'] = candidate


def record_cleanup(record, success, executor):
    diag = record['diagnostics']
    diag['cleanup'] = 'PASSED' if success else 'FAILED'
    if not success and diag['cleanupError'] == 'NONE':
        diag.update(cleanupStage=failure_stage(executor), cleanupError='CLEANUP_UNPROVEN')
    validate_diagnostics(diag)


def diagnostic_summary(record):
    """Only a validated finite projection may enter hosted stdout, never IDs."""
    diag = validate_diagnostics(record['diagnostics'])
    return 'CI_BOOTSTRAP_DIAGNOSTICS ' + json.dumps(diag, separators=(',', ':'), sort_keys=True)
