import { useReducer, useCallback } from 'react';
import type { CanonicalRole } from '../../types/cci';
import type { ResumeIntake, LiveResult } from '../../lib/live-analysis';
import type { EvaluationStep } from './EvaluationSteps';
import type { SourceSelection } from './SourceManifestStep';

export type Phase = 'idle' | 'upload' | 'analyze';

export interface EvaluationState {
  intake: ResumeIntake | null;
  fileName: string;
  fileSize: number;
  sources: SourceSelection[];
  identity: string;
  role: CanonicalRole;
  jd: string;
  backendJdText: string;
  backendJobId: string | null;
  jdFileName: string;
  jdFileSize: number;
  jdLoading: boolean;
  jdError: string;
  jdWarning: string;
  phase: Phase;
  step: EvaluationStep;
  error: string;
  sourceError: string;
  showWizard: boolean;
  result: LiveResult | null;
  previousRunNotice: string;
  hrSavedNotice: string;
}

export const initialEvaluationState: EvaluationState = {
  intake: null,
  fileName: '',
  fileSize: 0,
  sources: [],
  identity: '',
  role: 'backend',
  jd: '',
  backendJdText: '',
  backendJobId: null,
  jdFileName: '',
  jdFileSize: 0,
  jdLoading: false,
  jdError: '',
  jdWarning: '',
  phase: 'idle',
  step: 0,
  error: '',
  sourceError: '',
  showWizard: true,
  result: null,
  previousRunNotice: '',
  hrSavedNotice: '',
};

export type EvaluationAction =
  | { type: 'SET_INTAKE'; payload: ResumeIntake | null }
  | { type: 'SET_FILE_NAME'; payload: string }
  | { type: 'SET_FILE_SIZE'; payload: number }
  | { type: 'SET_ROLE'; payload: CanonicalRole }
  | { type: 'SET_JD'; payload: string }
  | { type: 'SET_BACKEND_JD_TEXT'; payload: string }
  | { type: 'SET_BACKEND_JOB_ID'; payload: string | null }
  | { type: 'SET_JD_FILE_NAME'; payload: string }
  | { type: 'SET_JD_FILE_SIZE'; payload: number }
  | { type: 'SET_JD_LOADING'; payload: boolean }
  | { type: 'SET_JD_ERROR'; payload: string }
  | { type: 'SET_JD_WARNING'; payload: string }
  | { type: 'SET_SOURCES'; payload: SourceSelection[] | ((prev: SourceSelection[]) => SourceSelection[]) }
  | { type: 'SET_IDENTITY'; payload: string }
  | { type: 'SET_STEP'; payload: EvaluationStep }
  | { type: 'SET_PHASE'; payload: Phase }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'SET_SOURCE_ERROR'; payload: string }
  | { type: 'SET_SHOW_WIZARD'; payload: boolean }
  | { type: 'SET_RESULT'; payload: LiveResult | null }
  | { type: 'SET_PREVIOUS_RUN_NOTICE'; payload: string }
  | { type: 'SET_HR_SAVED_NOTICE'; payload: string }
  | { type: 'RESUME_UPLOAD_SUCCESS'; payload: { intake: ResumeIntake; fileName: string; fileSize: number; sources: SourceSelection[]; identity: string } }
  | { type: 'REMOVE_RESUME' }
  | { type: 'JD_UPLOAD_START' }
  | { type: 'JD_UPLOAD_SUCCESS'; payload: { text: string; fileName: string; fileSize: number; jobId?: string | null; warning?: string } }
  | { type: 'JD_UPLOAD_ERROR'; payload: string }
  | { type: 'REMOVE_JD' }
  | { type: 'RESET_WORKFLOW' };

export function evaluationReducer(state: EvaluationState, action: EvaluationAction): EvaluationState {
  switch (action.type) {
    case 'SET_INTAKE':
      return { ...state, intake: action.payload };
    case 'SET_FILE_NAME':
      return { ...state, fileName: action.payload };
    case 'SET_FILE_SIZE':
      return { ...state, fileSize: action.payload };
    case 'SET_ROLE':
      return { ...state, role: action.payload };
    case 'SET_JD':
      return { ...state, jd: action.payload };
    case 'SET_BACKEND_JD_TEXT':
      return { ...state, backendJdText: action.payload };
    case 'SET_BACKEND_JOB_ID':
      return { ...state, backendJobId: action.payload };
    case 'SET_JD_FILE_NAME':
      return { ...state, jdFileName: action.payload };
    case 'SET_JD_FILE_SIZE':
      return { ...state, jdFileSize: action.payload };
    case 'SET_JD_LOADING':
      return { ...state, jdLoading: action.payload };
    case 'SET_JD_ERROR':
      return { ...state, jdError: action.payload };
    case 'SET_JD_WARNING':
      return { ...state, jdWarning: action.payload };
    case 'SET_SOURCES':
      return {
        ...state,
        sources: typeof action.payload === 'function' ? action.payload(state.sources) : action.payload,
      };
    case 'SET_IDENTITY':
      return { ...state, identity: action.payload };
    case 'SET_STEP':
      return { ...state, step: action.payload };
    case 'SET_PHASE':
      return { ...state, phase: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload };
    case 'SET_SOURCE_ERROR':
      return { ...state, sourceError: action.payload };
    case 'SET_SHOW_WIZARD':
      return { ...state, showWizard: action.payload };
    case 'SET_RESULT':
      return { ...state, result: action.payload };
    case 'SET_PREVIOUS_RUN_NOTICE':
      return { ...state, previousRunNotice: action.payload };
    case 'SET_HR_SAVED_NOTICE':
      return { ...state, hrSavedNotice: action.payload };
    case 'RESUME_UPLOAD_SUCCESS':
      return {
        ...state,
        intake: action.payload.intake,
        fileName: action.payload.fileName,
        fileSize: action.payload.fileSize,
        sources: action.payload.sources,
        identity: action.payload.identity,
        step: 0,
        phase: 'idle',
        error: '',
      };
    case 'REMOVE_RESUME':
      return {
        ...state,
        intake: null,
        fileName: '',
        fileSize: 0,
        sources: [],
        identity: '',
        step: 0,
        error: '',
      };
    case 'JD_UPLOAD_START':
      return {
        ...state,
        jdLoading: true,
        jdError: '',
        jdWarning: '',
      };
    case 'JD_UPLOAD_SUCCESS':
      return {
        ...state,
        jdLoading: false,
        backendJdText: action.payload.text,
        jd: action.payload.text,
        jdFileName: action.payload.fileName,
        jdFileSize: action.payload.fileSize,
        backendJobId: action.payload.jobId || null,
        jdWarning: action.payload.warning || '',
        jdError: '',
      };
    case 'JD_UPLOAD_ERROR':
      return {
        ...state,
        jdLoading: false,
        jdError: action.payload,
      };
    case 'REMOVE_JD':
      return {
        ...state,
        jdFileName: '',
        jdFileSize: 0,
        backendJdText: '',
        backendJobId: null,
        jd: '',
        jdError: '',
        jdWarning: '',
      };
    case 'RESET_WORKFLOW':
      return initialEvaluationState;
    default:
      return state;
  }
}

export function useEvaluationWorkflow() {
  const [state, dispatch] = useReducer(evaluationReducer, initialEvaluationState);

  const setIntake = useCallback((intake: ResumeIntake | null) => dispatch({ type: 'SET_INTAKE', payload: intake }), []);
  const setFileName = useCallback((name: string) => dispatch({ type: 'SET_FILE_NAME', payload: name }), []);
  const setFileSize = useCallback((size: number) => dispatch({ type: 'SET_FILE_SIZE', payload: size }), []);
  const setRole = useCallback((role: CanonicalRole) => dispatch({ type: 'SET_ROLE', payload: role }), []);
  const setJd = useCallback((jd: string) => dispatch({ type: 'SET_JD', payload: jd }), []);
  const setBackendJdText = useCallback((text: string) => dispatch({ type: 'SET_BACKEND_JD_TEXT', payload: text }), []);
  const setBackendJobId = useCallback((id: string | null) => dispatch({ type: 'SET_BACKEND_JOB_ID', payload: id }), []);
  const setJdFileName = useCallback((name: string) => dispatch({ type: 'SET_JD_FILE_NAME', payload: name }), []);
  const setJdFileSize = useCallback((size: number) => dispatch({ type: 'SET_JD_FILE_SIZE', payload: size }), []);
  const setJdLoading = useCallback((loading: boolean) => dispatch({ type: 'SET_JD_LOADING', payload: loading }), []);
  const setJdError = useCallback((err: string) => dispatch({ type: 'SET_JD_ERROR', payload: err }), []);
  const setJdWarning = useCallback((warn: string) => dispatch({ type: 'SET_JD_WARNING', payload: warn }), []);
  const setSources = useCallback((sources: SourceSelection[] | ((prev: SourceSelection[]) => SourceSelection[])) => {
    dispatch({ type: 'SET_SOURCES', payload: sources });
  }, []);
  const setIdentity = useCallback((identity: string) => dispatch({ type: 'SET_IDENTITY', payload: identity }), []);
  const setStep = useCallback((step: EvaluationStep) => dispatch({ type: 'SET_STEP', payload: step }), []);
  const setPhase = useCallback((phase: Phase) => dispatch({ type: 'SET_PHASE', payload: phase }), []);
  const setError = useCallback((error: string) => dispatch({ type: 'SET_ERROR', payload: error }), []);
  const setSourceError = useCallback((error: string) => dispatch({ type: 'SET_SOURCE_ERROR', payload: error }), []);
  const setShowWizard = useCallback((show: boolean) => dispatch({ type: 'SET_SHOW_WIZARD', payload: show }), []);
  const setResult = useCallback((result: LiveResult | null) => dispatch({ type: 'SET_RESULT', payload: result }), []);
  const setPreviousRunNotice = useCallback((notice: string) => dispatch({ type: 'SET_PREVIOUS_RUN_NOTICE', payload: notice }), []);
  const setHrSavedNotice = useCallback((notice: string) => dispatch({ type: 'SET_HR_SAVED_NOTICE', payload: notice }), []);

  return {
    state,
    dispatch,
    setIntake,
    setFileName,
    setFileSize,
    setRole,
    setJd,
    setBackendJdText,
    setBackendJobId,
    setJdFileName,
    setJdFileSize,
    setJdLoading,
    setJdError,
    setJdWarning,
    setSources,
    setIdentity,
    setStep,
    setPhase,
    setError,
    setSourceError,
    setShowWizard,
    setResult,
    setPreviousRunNotice,
    setHrSavedNotice,
  };
}
