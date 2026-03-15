import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DiagnosisCard } from './DiagnosisCard';
import { makeDiagnosis, makeDiagnosisCause, makeDiagnosisRecommendedPart } from '@/test/fixtures';

describe('DiagnosisCard', () => {
  it('renders symptom header', () => {
    render(<DiagnosisCard data={makeDiagnosis()} />);
    expect(screen.getByText('Diagnosis: Ice maker not working')).toBeInTheDocument();
  });

  it('renders cause names', () => {
    render(<DiagnosisCard data={makeDiagnosis()} />);
    expect(screen.getByText('Faulty Water Inlet Valve')).toBeInTheDocument();
  });

  it('renders high likelihood with correct label', () => {
    render(<DiagnosisCard data={makeDiagnosis({ causes: [makeDiagnosisCause({ likelihood: 'High' })] })} />);
    expect(screen.getByText('High')).toBeInTheDocument();
  });

  it('renders medium likelihood label', () => {
    render(<DiagnosisCard data={makeDiagnosis({ causes: [makeDiagnosisCause({ likelihood: 'Medium' })] })} />);
    expect(screen.getByText('Medium')).toBeInTheDocument();
  });

  it('renders low likelihood label', () => {
    render(<DiagnosisCard data={makeDiagnosis({ causes: [makeDiagnosisCause({ likelihood: 'Low' })] })} />);
    expect(screen.getByText('Low')).toBeInTheDocument();
  });

  it('renders recommended parts', () => {
    render(<DiagnosisCard data={makeDiagnosis()} />);
    expect(screen.getByText('Water Inlet Valve')).toBeInTheDocument();
    expect(screen.getByText('$47.82')).toBeInTheDocument();
  });

  it('renders follow-up questions', () => {
    render(<DiagnosisCard data={makeDiagnosis()} />);
    expect(screen.getByText('When did the issue start?')).toBeInTheDocument();
  });

  it('handles empty causes array', () => {
    render(<DiagnosisCard data={makeDiagnosis({ causes: [] })} />);
    expect(screen.queryByText('Possible Causes')).toBeNull();
  });

  it('handles empty recommended_parts and follow_up_questions', () => {
    render(<DiagnosisCard data={makeDiagnosis({ recommended_parts: [], follow_up_questions: [] })} />);
    expect(screen.queryByText('Recommended Parts')).toBeNull();
    expect(screen.queryByText(/To help diagnose/)).toBeNull();
  });
});
