"""Offline-only debug excerpt, privacy, lifetime and disposal; no real Claude."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import time
import unittest
from unittest import mock
from terminal_input_policy import TerminalInputPolicy
from terminal_input_challenge import create_offline_probe_issuer, InputProofError
import terminal_input_challenge as challenge
from terminal_state_adapter import TerminalCell, TerminalSnapshot, TerminalState, COUNT_KEYS

FACTS={'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True}


def frame(rejected='❯ /context',extra=(),dense=False):
    lines={0:'Context Usage',1:'Free space: 90%',2:'Autocompact buffer: 3%',5:rejected,37:'❯\u00a0',**dict(extra)}
    rows=[]
    for y in range(40):
        row=[TerminalCell(char,1) for char in lines.get(y,'')]
        row.extend(TerminalCell('z'*16 if dense else '',1) for _ in range(120-len(row)))
        rows.append(tuple(row))
    return TerminalSnapshot('alternate',2,37,0,0,tuple(rows),{key:0 for key in COUNT_KEYS})


def rejection():
    return InputProofError('INPUT_PROBE_INELIGIBLE','UNSUPPORTED_ROW',
        input_row_relation='OTHER_CAPTURED_ROW',input_row_cause='CONTROL_COMMAND_SHAPE')


def edit_report_fixture():
    return {'networkIsolated':True,'operatorStateHidden':True,'capabilitiesDropped':True,
        'runtime':'1.2.3','reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','cases':[{
            'case':'text-turn','beforeExit':2,'sdkExit':2,'afterExit':2,'caseRootAbsent':True,
            'contextInspected':False,'naturalExit':False,'messages':0,'skillCalls':0,'validSkillSample':False,
            'stages':[{'phase':'before','events':[{'stage':'context_inspected','outcome':'failed'}],
                'diagnostics':{'records':[{'point':'failure','reasonCode':'INPUT_PROBE_REVOKED',
                    'contextCommandFailure':{'phase':'EDIT_PENDING','check':'NORMALIZED_ELIGIBILITY',
                        'commandBytesWritten':8,'enterBytesWritten':0},
                    'normalizedInputFailure':{'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW',
                        'rowCause':'UNRECOGNIZED_SHAPE'}},
                    {'point':'native_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True},
                    {'point':'helper_cleanup','reasonCode':'CLEANUP_COMPLETED','leaderReaped':True}],
                    'rejected':False,'truncated':False}}]}]}


class TerminalContextDebugTests(unittest.TestCase):
    def setUp(self):
        path=Path(__file__).with_name('terminal_context_debug.py')
        self.assertTrue(path.is_file(),'sealed offline context debug capture missing')
        spec=importlib.util.spec_from_file_location('terminal_context_debug',path)
        self.m=importlib.util.module_from_spec(spec); spec.loader.exec_module(self.m)
        self.temp=tempfile.TemporaryDirectory(prefix='context-debug-test-'); self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'case'; self.root.mkdir(mode=0o700)
        self.state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
            Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
        self.addCleanup(self.state.close)
        with mock.patch.object(challenge,'audit_offline_namespace',return_value=FACTS):
            self.scope=create_offline_probe_issuer().issue_scope(self.state,object())

    def debug(self):
        with mock.patch.object(self.m,'audit_offline_namespace',return_value=FACTS):
            return self.m.create_context_debug(self.scope,self.state,self.root)

    def capture(self,debug,snapshot=None,error=None,**kwargs):
        with mock.patch.object(self.m,'audit_offline_namespace',return_value=FACTS):
            debug.capture(self.state,self.scope,snapshot or frame(),error or rejection(),
                numeric_context=True,**kwargs)

    def dispose(self):
        # Exact test-owned directory under the unique TemporaryDirectory.
        self.assertEqual(self.root.parent,Path(self.temp.name))
        self.assertFalse(self.root.is_symlink()); shutil.rmtree(self.root)

    def edit_capture_fixture(self,snapshot=None,*,phase='EDIT_PENDING',check='NORMALIZED_ELIGIBILITY',
                             count=8,enter=0,detail=None):
        from dataclasses import replace
        import terminal_context_echo as echo
        from terminal_context_diagnostics import _create_context_journal
        self.assertTrue(callable(getattr(self.m,'create_context_edit_debug',None)),
            'memory-only edit capture missing')
        if not getattr(self,'_edit_fixture_used',False):
            for target in (self.m,challenge):
                patch=mock.patch.object(target,'audit_offline_namespace',return_value=FACTS)
                patch.start(); self.addCleanup(patch.stop)
        if getattr(self,'_edit_fixture_used',False):
            self.state=TerminalState(Path(os.environ['P004B_TERMINAL_NODE']),
                Path(os.environ['P004B_TERMINAL_MODULE_ROOT']),time.monotonic()+20)
            self.addCleanup(self.state.close)
            with mock.patch.object(challenge,'audit_offline_namespace',return_value=FACTS):
                self.scope=create_offline_probe_issuer().issue_scope(self.state,object())
        self._edit_fixture_used=True
        empty=frame(''); rows=list(empty.rows)
        for index in (0,1,2): rows[index]=tuple(TerminalCell('',1) for _ in range(120))
        empty=replace(empty,rows=tuple(rows))
        policy=TerminalInputPolicy(); owner=object(); controller=object()
        native=mock.Mock(); native.poll.return_value=None
        bindings={'controller_owner':controller,'scope':self.scope,'state':self.state,'transition_owner':owner}
        journal=_create_context_journal(**bindings); self.addCleanup(journal.finish)
        with mock.patch.object(self.m,'audit_offline_namespace',return_value=FACTS):
            capture=self.m.create_context_edit_debug(self.scope,self.state,self.root)
        self.addCleanup(capture.finish)
        observer=capture.bind(controller_owner=controller,transition_owner=owner,journal=journal)
        command=echo.begin_context_command(self.scope,self.state,native,owner,policy,empty,1,_diagnostic_journal=journal)
        self.addCleanup(command.invalidate,'INPUT_PROBE_REVOKED'); record=echo._COMMANDS[command]
        observer.bind_command(record); command.type_bytes(empty,1)
        if count: journal.acknowledge(count,submission=False,remaining=8)
        if enter: journal.acknowledge(enter,submission=True,remaining=1)
        command.check_edit(empty,1,8); journal.set_phase(phase)
        snapshot=snapshot or frame('❯ /context synthetic description')
        rows=list(snapshot.rows)
        rows[37]=tuple([TerminalCell(c,1) for c in '❯\u00a0/context']+[TerminalCell('',1)]*110)
        snapshot=replace(snapshot,cursorX=10,rows=tuple(rows))
        detail=detail or {'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'UNRECOGNIZED_SHAPE'}
        assessment=__import__('terminal_input_policy').EmptyInputAssessment(None,detail['reason'],
            detail.get('rowRelation'),detail.get('rowCause'))
        error=InputProofError('INPUT_PROBE_REVOKED')
        journal.freeze(error,check,normalized_input_failure=detail)
        observer.freeze(error,check,command_record=record,snapshot=snapshot,assessment=assessment,rejected_index=5)
        args={'controller_owner':controller,'transition_owner':owner,'journal':journal,'snapshot':snapshot}
        return capture,error,args

    def prepare_edit(self,capture,error,args):
        with mock.patch.object(self.m,'audit_offline_namespace',return_value=FACTS):
            capture.prepare(error,**args)

    def test_edit_capture_closed_boundary_and_no_file(self):
        capture,error,args=self.edit_capture_fixture()
        with mock.patch.object(self.m.os,'open',side_effect=AssertionError('new file opened')):
            self.prepare_edit(capture,error,args)
        self.assertEqual(list(self.root.iterdir()),[])
        self.assertNotIn('excerpt',capture.pending_report())
        # An early report consumes/omits rather than allowing later replay.
        self.dispose(); self.assertNotIn('excerpt',capture.pending_report())

    def test_edit_capture_sensitive_scan_and_unicode(self):
        capture,error,args=self.edit_capture_fixture(frame('❯ /context synthetic café 界\x1b'))
        self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
        pending=capture.pending_report()
        self.assertEqual(pending,{'status':'PREPARED','excerpt':{
            'rowRelation':'OTHER_CAPTURED_ROW','text':'❯ /context synthetic café 界\\u001b'}})
        self.assertNotIn('excerpt',capture.pending_report())

    def test_edit_capture_actual_byte_limits(self):
        from dataclasses import replace
        snapshot=frame('❯ /context synthetic description'); rows=list(snapshot.rows)
        rows[5]=tuple([TerminalCell('❯',1)]+[TerminalCell('界'*16,1)]*119)
        capture,error,args=self.edit_capture_fixture(replace(snapshot,rows=tuple(rows)))
        self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
        self.assertEqual(capture.pending_report(),{'status':'OMITTED_EXCERPT_LIMIT'})

    def test_edit_capture_observer_loss_omits(self):
        capture,error,args=self.edit_capture_fixture()
        with mock.patch.object(self.m,'_sensitive',side_effect=LookupError('synthetic detector loss')):
            self.prepare_edit(capture,error,args)
        capture.finish(); self.dispose()
        self.assertNotIn('excerpt',capture.pending_report())

    def test_edit_capture_sensitive_material_outside_row_omits(self):
        capture,error,args=self.edit_capture_fixture(frame('❯ /context synthetic description',
            extra=((22,'Password synthetic diagnostic fixture'),)))
        self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
        pending=capture.pending_report()
        self.assertTrue(pending=={'status':'OMITTED_SENSITIVE'},'sensitive diagnostic escaped')

    def test_edit_capture_tuple_and_scope_mismatches(self):
        cases=({'phase':'SUBMIT_PENDING'},{'check':'PREFIX_CELLS'},{'count':7},{'enter':1},
            {'detail':{'reason':'UNSUPPORTED_ROW','rowRelation':'CURSOR_ROW','rowCause':'UNRECOGNIZED_SHAPE'}},
            {'detail':{'reason':'UNSUPPORTED_ROW','rowRelation':'OTHER_CAPTURED_ROW','rowCause':'CONTROL_COMMAND_SHAPE'}})
        for changes in cases:
            capture,error,args=self.edit_capture_fixture(**changes)
            self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
            self.assertNotIn('excerpt',capture.pending_report())
            self.root.mkdir(mode=0o700)
        capture,error,args=self.edit_capture_fixture()
        with mock.patch.object(self.m.time,'monotonic',return_value=time.monotonic()+100):
            self.prepare_edit(capture,error,args)
        capture.finish(); self.dispose()
        self.assertEqual(capture.pending_report(),{'status':'OMITTED_SCOPE'})

    def test_edit_capture_exact_export_size_and_wide_cells(self):
        from dataclasses import replace
        for size in (4096,4097):
            base='❯ /context '
            overhead=len(json.dumps({'rowRelation':'OTHER_CAPTURED_ROW','text':base},sort_keys=True).encode())
            count,remainder=divmod(size-overhead,6)
            text=base+'界'*count+'a'*remainder
            cells=[TerminalCell(text[index:index+16],1) for index in range(0,len(text),16)]
            cells.extend(TerminalCell('',1) for _ in range(120-len(cells)))
            snapshot=frame(); rows=list(snapshot.rows); rows[5]=tuple(cells)
            capture,error,args=self.edit_capture_fixture(replace(snapshot,rows=tuple(rows)))
            self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
            pending=capture.pending_report()
            if size==4096:
                self.assertEqual(pending['status'],'PREPARED')
                self.assertEqual(len(json.dumps(pending['excerpt'],sort_keys=True).encode()),4096)
            else: self.assertEqual(pending,{'status':'OMITTED_EXCERPT_LIMIT'})
            self.root.mkdir(mode=0o700)
        snapshot=frame('❯ /context synthetic description'); rows=list(snapshot.rows); row=list(rows[5])
        row[40]=TerminalCell('界',2); row[41]=TerminalCell('',0); rows[5]=tuple(row)
        capture,error,args=self.edit_capture_fixture(replace(snapshot,rows=tuple(rows)))
        self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
        self.assertEqual(capture.pending_report()['status'],'PREPARED')

    def test_edit_capture_malformed_row_and_root_refuse(self):
        from dataclasses import replace
        snapshot=frame('❯ /context synthetic description'); rows=list(snapshot.rows)
        rows[5]=rows[5]+(TerminalCell('',1),)
        capture,error,args=self.edit_capture_fixture(replace(snapshot,rows=tuple(rows)))
        self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
        self.assertNotIn('excerpt',capture.pending_report())
        self.root.mkdir(mode=0o700)
        capture,error,args=self.edit_capture_fixture(); self.root.chmod(0o755)
        self.prepare_edit(capture,error,args); capture.finish(); self.dispose()
        self.assertEqual(capture.pending_report(),{'status':'OMITTED_SCOPE'})

    def test_edit_capture_factory_rejects_host_and_forged(self):
        self.assertTrue(callable(getattr(self.m,'create_context_edit_debug',None)),
            'memory-only edit capture missing')
        with self.assertRaises(RuntimeError): self.m.create_context_edit_debug(self.scope,self.state,self.root)
        with self.assertRaises(RuntimeError): self.m.validate_context_edit_debug({},self.state,self.scope)

    def test_edit_promotion_requires_parent_disposal(self):
        import copy
        self.assertTrue(callable(getattr(self.m,'finalize_edit_report',None)),'parent edit promotion missing')
        base=edit_report_fixture()
        pending={'status':'PREPARED','excerpt':{'rowRelation':'OTHER_CAPTURED_ROW','text':'❯ /context synthetic description'}}
        self.assertNotIn('excerpt',self.m.finalize_edit_report(base,pending,disposal_proven=False)['debugContextEdit'])
        public=self.m.finalize_edit_report(base,pending,disposal_proven=True)
        self.assertEqual(public['debugContextEdit'],{'status':'READY','untrustedData':True,
            'chatCopyMayPersist':True,'excerpt':pending['excerpt']})
        self.assertEqual(public['cases'],base['cases'])
        for fault in ('case','native','helper'):
            changed=copy.deepcopy(base)
            if fault=='case': changed['cases'][0]['caseRootAbsent']=False
            else:
                index=1 if fault=='native' else 2
                changed['cases'][0]['stages'][0]['diagnostics']['records'][index]['leaderReaped']=False
            result=self.m.finalize_edit_report(changed,pending,disposal_proven=True)
            self.assertNotIn('excerpt',result['debugContextEdit'])
        self.assertNotIn('excerpt',self.m.finalize_edit_report(base,{**pending,'status':'READY'},
            disposal_proven=False)['debugContextEdit'])

    def test_edit_candidate_closed_shapes_and_report_budget(self):
        self.assertTrue(callable(getattr(self.m,'finalize_edit_report',None)),'parent edit promotion missing')
        base=edit_report_fixture()
        for pending in (None,{}, {'status':'READY'}, {'status':'PREPARED'},
                {'status':'NO_CAPTURE','text':'synthetic unexpected'},
                {'status':'PREPARED','excerpt':{'rowRelation':'CURSOR_ROW','text':'synthetic'}},
                {'status':'PREPARED','excerpt':{'rowRelation':'OTHER_CAPTURED_ROW','text':None}},
                {'status':'PREPARED','excerpt':{'rowRelation':'OTHER_CAPTURED_ROW','text':'x'*4096}},
                {'status':'PREPARED','excerpt':{'rowRelation':'OTHER_CAPTURED_ROW','text':'synthetic','extra':True}}):
            result=self.m.finalize_edit_report(base,pending,disposal_proven=True)
            self.assertEqual(result['cases'],base['cases'])
            self.assertNotIn('excerpt',result['debugContextEdit'])
            self.assertLessEqual(len((json.dumps(result,sort_keys=True)+'\n').encode()),16384)
        bad={**base,'unrecognized':'synthetic unexpected'}
        result=self.m.finalize_edit_report(bad,{'status':'NO_CAPTURE'},disposal_proven=True)
        self.assertNotIn('unrecognized',result)
        self.assertNotIn('synthetic unexpected',json.dumps(result))

    def test_edit_four_phase_budget_omits_whole_excerpt(self):
        import copy
        from terminal_structural_diagnostics import TerminalDiagnostics
        self.assertTrue(callable(getattr(self.m,'finalize_edit_report',None)),'parent edit promotion missing')
        base=edit_report_fixture(); failed=copy.deepcopy(base['cases'][0]['stages'][0])
        structure={'buffer':'alternate','cursorX':120,'cursorY':39,'baseY':0,'viewportY':0,
            'candidateCount':40,'inputFresh':True,'contextFresh':True,'locationFresh':True,
            'authentication':'NONE','readiness':'CANDIDATE_COUNT'}
        def phase(name,failure=False):
            collector=TerminalDiagnostics()
            for row in failed['diagnostics']['records'][0 if failure else 1:]:
                collector.add(row['point'],row['reasonCode'],**{k:v for k,v in row.items() if k not in ('point','reasonCode')})
            for _ in range(16): collector.add('initial','CHECKPOINT',structure=structure)
            return {'phase':name,'events':[{'stage':'prompt_ready','outcome':'passed'}]*8,'diagnostics':collector.report()}
        first=base['cases'][0]
        first.update(beforeExit=0,sdkExit=0,afterExit=0,contextInspected=True,naturalExit=True,
            stages=[phase('before'),phase('after')])
        second=copy.deepcopy(first); second.update(case='skill-turn',afterExit=2,contextInspected=False,
            naturalExit=False,skillCalls=1,validSkillSample=True,stages=[phase('before'),phase('after',True)])
        base['cases'].append(second)
        text='❯ /context '+'界'*650
        pending={'status':'PREPARED','excerpt':{'rowRelation':'OTHER_CAPTURED_ROW','text':text}}
        self.assertLessEqual(len(json.dumps(pending['excerpt'],sort_keys=True).encode()),4096)
        public=self.m.finalize_edit_report(base,pending,disposal_proven=True)
        self.assertEqual(public['cases'],base['cases'])
        self.assertEqual(public['debugContextEdit']['status'],'OMITTED_REPORT_LIMIT')
        self.assertNotIn('excerpt',public['debugContextEdit'])
        self.assertLessEqual(len((json.dumps(public,sort_keys=True)+'\n').encode()),16384)
        inner=self.m._fit_edit_pending_report(base,pending)
        self.assertEqual(inner['_pendingContextEdit'],{'status':'OMITTED_REPORT_LIMIT'})
        self.assertLessEqual(len((json.dumps(inner,sort_keys=True)+'\n').encode()),16384)

    def test_one_frame_and_minimal_untrusted_excerpt_only_after_disposal(self):
        debug=self.debug(); self.capture(debug)
        raw=self.root/'context-debug-frame.json'
        self.assertTrue(raw.is_file()); self.assertEqual(stat.S_IMODE(raw.stat().st_mode),0o600)
        self.assertLessEqual(raw.stat().st_size,131072)
        self.assertNotIn('excerpt',debug.report())
        self.dispose(); report=debug.report()
        self.assertEqual(report['status'],'READY'); self.assertTrue(report['untrustedData'])
        self.assertEqual([row['index'] for row in report['excerpt']['rows']],[5,37])
        self.assertEqual(report['excerpt']['rows'][0]['text'],'❯ /context')
        self.assertNotIn('Free space',json.dumps(report))
        self.assertLessEqual(len(json.dumps(report['excerpt'],sort_keys=True).encode()),4096)

    def test_capture_is_one_shot_without_overwriting_first_frame(self):
        debug=self.debug(); self.capture(debug)
        before=(self.root/'context-debug-frame.json').read_bytes()
        self.capture(debug,frame('❯ replacement'))
        self.assertEqual((self.root/'context-debug-frame.json').read_bytes(),before)
        self.dispose(); self.assertEqual(debug.report()['excerpt']['rows'][0]['text'],'❯ /context')

    def test_host_serialized_scope_and_foreign_state_cannot_activate(self):
        with self.assertRaises(RuntimeError): self.m.create_context_debug(self.scope,self.state,self.root)
        with mock.patch.object(self.m,'audit_offline_namespace',return_value=FACTS):
            with self.assertRaises(RuntimeError): self.m.create_context_debug({},self.state,self.root)
        debug=self.debug()
        with self.assertRaises(RuntimeError): self.m.validate_context_debug({'enabled':True},self.state,self.scope)
        with self.assertRaises(RuntimeError): self.m.validate_context_debug(debug,object(),self.scope)
        self.assertEqual(list(self.root.iterdir()),[])

    def test_authentication_and_sensitive_values_omit_entire_capture(self):
        for text,expected in (('Do you want to use this API key?','OMITTED_PROVENANCE'),
                     ('Password: synthetic-private-text','OMITTED_SENSITIVE'),
                     ('canary synthetic-private-text','OMITTED_SENSITIVE'),
                     ('p\u200bassword synthetic-private-text','OMITTED_SENSITIVE'),
                     ('Authorization: Bearer synthetic-private-text','OMITTED_SENSITIVE')):
            debug=self.debug(); self.capture(debug,frame(extra=((8,text),)))
            self.assertEqual(list(self.root.iterdir()),[])
            self.dispose(); report=debug.report()
            self.assertNotIn('excerpt',report); self.assertEqual(report['status'],expected)
            self.assertTrue('synthetic-private-text' not in json.dumps(report),'protected value leaked')
            self.root.mkdir(mode=0o700)

    def test_wrong_stage_and_metadata_never_capture(self):
        debug=self.debug()
        with mock.patch.object(self.m,'audit_offline_namespace',return_value=FACTS):
            debug.capture(self.state,self.scope,frame(),rejection(),numeric_context=False)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose(); self.assertNotIn('excerpt',debug.report())

    def test_original_deadline_and_cancellation_fence_file_creation(self):
        debug=self.debug()
        with mock.patch.object(self.m.time,'monotonic',return_value=self.state.operation_deadline+1):
            self.capture(debug)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose(); self.assertEqual(debug.report()['status'],'OMITTED_SCOPE')

    def test_frame_limit_omits_without_clipping_or_writing(self):
        error=InputProofError('INPUT_PROBE_INELIGIBLE','UNSUPPORTED_ROW',
            input_row_relation='OTHER_CAPTURED_ROW',input_row_cause='UNRECOGNIZED_SHAPE')
        debug=self.debug(); self.capture(debug,frame(dense=True),error)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose(); self.assertEqual(debug.report()['status'],'OMITTED_FRAME_LIMIT')

    def test_root_replacement_and_file_links_are_not_followed(self):
        debug=self.debug(); old=self.root.parent/'old'; self.root.rename(old); self.root.mkdir(mode=0o700)
        self.capture(debug)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose(); self.assertNotIn('excerpt',debug.report())
        self.root.mkdir(mode=0o700); debug=self.debug()
        target=self.root.parent/'sentinel'; target.write_text('unchanged')
        (self.root/'context-debug-frame.json').symlink_to(target)
        self.capture(debug)
        self.assertEqual(target.read_text(),'unchanged')
        self.dispose(); self.assertNotIn('excerpt',debug.report())

    def test_ui_controls_are_escaped_and_not_executable_terminal_bytes(self):
        current=frame('❯\u200b/context')
        error=InputProofError('INPUT_PROBE_INELIGIBLE','UNSUPPORTED_ROW',
            input_row_relation='OTHER_CAPTURED_ROW',input_row_cause='INVISIBLE_FORMAT_CHAR')
        debug=self.debug(); self.capture(debug,current,error)
        self.dispose(); text=debug.report()['excerpt']['rows'][0]['text']
        self.assertIn('\\u200b',text); self.assertNotIn('\u200b',text)

    def test_report_budget_omits_content_without_promoting_acceptance(self):
        base={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','padding':'a'*15000}
        debug={'status':'READY','untrustedData':True,'excerpt':{'text':'b'*4090}}
        report=self.m.fit_debug_report(base,debug)
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertEqual(report['debugContext']['status'],'OMITTED_REPORT_LIMIT')
        self.assertNotIn('excerpt',report['debugContext'])
        self.assertLessEqual(len(json.dumps(report,sort_keys=True).encode()),16320)

    def test_report_budget_includes_audit_disposal_and_print_newline(self):
        debug={'status':'READY','excerpt':{'text':'synthetic'*20}}
        base={'reasonCode':'OFFLINE_CONTROLS_INCONCLUSIVE','padding':''}
        overhead=len(json.dumps({**base,'debugContext':debug},sort_keys=True).encode())
        base['padding']='a'*(16320-overhead)
        report=self.m.fit_debug_report(base,debug)
        self.assertEqual(report['reasonCode'],'OFFLINE_CONTROLS_INCONCLUSIVE')
        self.assertEqual(report['debugContext']['status'],'OMITTED_REPORT_LIMIT')
        complete={**FACTS,**report,'disposableRootAbsent':True}
        self.assertLessEqual(len((json.dumps(complete,sort_keys=True)+'\n').encode()),16384)
        self.assertNotIn('excerpt',report['debugContext'])

    def test_excerpt_limit_omits_without_clipping_and_raw_frame_is_disposed(self):
        from dataclasses import replace
        snapshot=frame(); rows=list(snapshot.rows)
        for index in (5,37):
            rows[index]=tuple(list(rows[index][:12])+[TerminalCell('q'*16,1)]*108)
        snapshot=replace(snapshot,rows=tuple(rows))
        error=InputProofError('INPUT_PROBE_INELIGIBLE','UNSUPPORTED_ROW',
            input_row_relation='OTHER_CAPTURED_ROW',input_row_cause='UNRECOGNIZED_SHAPE')
        debug=self.debug(); self.capture(debug,snapshot,error)
        self.assertTrue((self.root/'context-debug-frame.json').is_file())
        self.dispose(); report=debug.report()
        self.assertEqual(report['status'],'OMITTED_EXCERPT_LIMIT'); self.assertNotIn('excerpt',report)

    def test_cancellation_and_write_failure_never_export_content(self):
        debug=self.debug()
        with mock.patch.object(self.state,'check_cancelled',side_effect=RuntimeError('synthetic interruption')):
            self.capture(debug)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose(); self.assertNotIn('excerpt',debug.report())
        self.root.mkdir(mode=0o700); debug=self.debug()
        with mock.patch.object(self.m.os,'write',side_effect=OSError('synthetic write failure')):
            self.capture(debug)
        self.dispose(); self.assertNotIn('excerpt',debug.report())

    def test_changed_root_permissions_refuse_capture(self):
        debug=self.debug(); self.root.chmod(0o755)
        self.capture(debug)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose(); self.assertNotIn('excerpt',debug.report())

    def test_forged_attached_projection_never_falls_back_to_default_row(self):
        error=rejection(); error._context_rejection={'row':5}
        debug=self.debug(); self.capture(debug,frame(),error)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose()
        self.assertEqual(debug.report()['status'],'OMITTED_PROVENANCE')

    def test_valid_projection_exports_actual_row_but_wrong_source_omits(self):
        from dataclasses import replace
        import terminal_context_echo as echo
        with mock.patch.object(challenge,'audit_offline_namespace',return_value=FACTS):
            policy=TerminalInputPolicy(); native=mock.Mock(); native.poll.return_value=None
            empty=frame(''); rows=list(empty.rows)
            for y in (0,1,2): rows[y]=tuple(TerminalCell('',1) for _ in range(120))
            empty=replace(empty,rows=tuple(rows))
            command=echo.begin_context_command(self.scope,self.state,native,object(),policy,empty,1)
            command.type_bytes(empty,1); command.check_edit(empty,1,8)
            rows=list(empty.rows); rows[37]=tuple([TerminalCell(c,1) for c in '❯\u00a0/context']+
                [TerminalCell('',1)]*110)
            typed=replace(empty,cursorX=10,rows=tuple(rows))
            command.observe(typed,2); command.submit_bytes(typed,2); command.submission_written(1)
            actual=frame(extra=((12,'❯ unknown'),))
            with self.assertRaises(InputProofError) as caught: command.bind_history(actual,3)
        debug=self.debug(); self.capture(debug,actual,caught.exception)
        self.dispose(); report=debug.report()
        self.assertEqual(report['status'],'READY')
        self.assertEqual(report['excerpt']['rows'][0]['index'],12)
        self.root.mkdir(mode=0o700)
        debug=self.debug(); self.capture(debug,replace(actual),caught.exception)
        self.assertEqual(list(self.root.iterdir()),[])
        self.dispose(); self.assertEqual(debug.report()['status'],'OMITTED_PROVENANCE')


if __name__=='__main__': unittest.main()
