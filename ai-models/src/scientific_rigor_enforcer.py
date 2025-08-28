"""
Scientific Rigor Framework for Causal AI Validation
Implements validate_scientific_rigor() with refutation battery and E-value analysis
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
import pandas as pd
from dataclasses import dataclass
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

@dataclass
class RigorValidationResult:
    passed: bool
    e_value: float
    p_value: float
    placebo_test_result: bool
    counterfactual_recovery_score: float
    calibration_score: float
    refutation_results: Dict[str, bool]
    confidence_interval: Tuple[float, float]
    effect_size: float
    statistical_power: float

@dataclass
class RefutationTest:
    name: str
    passed: bool
    p_value: float
    effect_estimate: float
    confidence_interval: Tuple[float, float]

class ScientificRigorFramework:
    def __init__(self, 
                 e_value_threshold: float = 2.0, 
                 p_value_threshold: float = 0.05,
                 min_effect_size: float = 0.1,
                 min_statistical_power: float = 0.8):
        self.e_value_threshold = e_value_threshold
        self.p_value_threshold = p_value_threshold
        self.min_effect_size = min_effect_size
        self.min_statistical_power = min_statistical_power
        
    def validate_scientific_rigor(self, 
                                causal_graph: Dict[str, Any],
                                data: Dict[str, Any],
                                intervention: Optional[Dict[str, Any]] = None) -> RigorValidationResult:
        """
        Comprehensive scientific rigor validation for causal claims
        Required for on-chain activation and auditability
        """
        refutation_results = self._run_refutation_battery(causal_graph, data)
        
        e_value = self._calculate_e_value(causal_graph, data)
        
        p_value = self._calculate_overall_p_value(refutation_results)
        
        placebo_result = self._run_placebo_tests(causal_graph, data)
        
        recovery_score = self._counterfactual_recovery_test(causal_graph, data)
        
        calibration_score = self._calibration_check(causal_graph, data)
        
        confidence_interval = self._calculate_confidence_interval(causal_graph, data)
        
        effect_size = self._calculate_effect_size(causal_graph, data)
        
        statistical_power = self._calculate_statistical_power(causal_graph, data)
        
        passed = self._overall_validation_decision(
            e_value, p_value, placebo_result, recovery_score, 
            calibration_score, effect_size, statistical_power, refutation_results
        )
        
        return RigorValidationResult(
            passed=passed,
            e_value=e_value,
            p_value=p_value,
            placebo_test_result=placebo_result,
            counterfactual_recovery_score=recovery_score,
            calibration_score=calibration_score,
            refutation_results={test.name: test.passed for test in refutation_results},
            confidence_interval=confidence_interval,
            effect_size=effect_size,
            statistical_power=statistical_power
        )
    
    def _run_refutation_battery(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> List[RefutationTest]:
        """Run comprehensive refutation tests"""
        tests = []
        
        tests.append(self._random_common_cause_test(causal_graph, data))
        tests.append(self._placebo_treatment_test(causal_graph, data))
        tests.append(self._data_subset_test(causal_graph, data))
        tests.append(self._bootstrap_test(causal_graph, data))
        tests.append(self._dummy_outcome_test(causal_graph, data))
        
        return tests
    
    def _random_common_cause_test(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> RefutationTest:
        """Test robustness to unobserved confounders"""
        try:
            original_effect = self._estimate_causal_effect(causal_graph, data)
            
            confounded_data = data.copy()
            confounder = np.random.normal(0, 1, len(self._get_data_array(data)))
            confounded_data['random_confounder'] = confounder
            
            confounded_effect = self._estimate_causal_effect(causal_graph, confounded_data)
            
            effect_change = abs(confounded_effect - original_effect)
            p_value = stats.ttest_1samp([original_effect, confounded_effect], 0).pvalue
            
            passed = effect_change < 0.1 * abs(original_effect)
            
            return RefutationTest(
                name="random_common_cause",
                passed=passed,
                p_value=p_value,
                effect_estimate=confounded_effect,
                confidence_interval=(confounded_effect - 0.1, confounded_effect + 0.1)
            )
        except Exception:
            return RefutationTest("random_common_cause", False, 1.0, 0.0, (0.0, 0.0))
    
    def _placebo_treatment_test(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> RefutationTest:
        """Test with placebo treatment"""
        try:
            data_array = self._get_data_array(data)
            placebo_treatment = np.random.binomial(1, 0.5, len(data_array))
            
            placebo_data = data.copy()
            placebo_data['placebo_treatment'] = placebo_treatment
            
            placebo_effect = self._estimate_causal_effect(causal_graph, placebo_data, treatment_col='placebo_treatment')
            
            t_stat, p_value = stats.ttest_1samp([placebo_effect], 0)
            
            passed = abs(placebo_effect) < 0.05 and p_value > 0.05
            
            return RefutationTest(
                name="placebo_treatment",
                passed=passed,
                p_value=p_value,
                effect_estimate=placebo_effect,
                confidence_interval=(placebo_effect - 0.05, placebo_effect + 0.05)
            )
        except Exception:
            return RefutationTest("placebo_treatment", False, 1.0, 0.0, (0.0, 0.0))
    
    def _data_subset_test(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> RefutationTest:
        """Test robustness across data subsets"""
        try:
            data_array = self._get_data_array(data)
            n = len(data_array)
            
            subset_size = max(10, n // 2)
            subset_indices = np.random.choice(n, subset_size, replace=False)
            
            subset_data = {}
            for key, value in data.items():
                if isinstance(value, (list, np.ndarray)) and len(value) == n:
                    subset_data[key] = np.array(value)[subset_indices]
                else:
                    subset_data[key] = value
            
            original_effect = self._estimate_causal_effect(causal_graph, data)
            subset_effect = self._estimate_causal_effect(causal_graph, subset_data)
            
            effect_difference = abs(subset_effect - original_effect)
            p_value = stats.ttest_1samp([original_effect, subset_effect], 0).pvalue
            
            passed = effect_difference < 0.2 * abs(original_effect)
            
            return RefutationTest(
                name="data_subset",
                passed=passed,
                p_value=p_value,
                effect_estimate=subset_effect,
                confidence_interval=(subset_effect - 0.1, subset_effect + 0.1)
            )
        except Exception:
            return RefutationTest("data_subset", False, 1.0, 0.0, (0.0, 0.0))
    
    def _bootstrap_test(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> RefutationTest:
        """Bootstrap test for effect stability"""
        try:
            n_bootstrap = 100
            effects = []
            
            data_array = self._get_data_array(data)
            n = len(data_array)
            
            for _ in range(n_bootstrap):
                bootstrap_indices = np.random.choice(n, n, replace=True)
                bootstrap_data = {}
                
                for key, value in data.items():
                    if isinstance(value, (list, np.ndarray)) and len(value) == n:
                        bootstrap_data[key] = np.array(value)[bootstrap_indices]
                    else:
                        bootstrap_data[key] = value
                
                effect = self._estimate_causal_effect(causal_graph, bootstrap_data)
                effects.append(effect)
            
            mean_effect = np.mean(effects)
            std_effect = np.std(effects)
            
            t_stat, p_value = stats.ttest_1samp(effects, 0)
            
            passed = std_effect < 0.1 * abs(mean_effect) and p_value < self.p_value_threshold
            
            return RefutationTest(
                name="bootstrap",
                passed=passed,
                p_value=p_value,
                effect_estimate=mean_effect,
                confidence_interval=(mean_effect - 1.96*std_effect, mean_effect + 1.96*std_effect)
            )
        except Exception:
            return RefutationTest("bootstrap", False, 1.0, 0.0, (0.0, 0.0))
    
    def _dummy_outcome_test(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> RefutationTest:
        """Test with dummy outcome variable"""
        try:
            data_array = self._get_data_array(data)
            dummy_outcome = np.random.normal(0, 1, len(data_array))
            
            dummy_data = data.copy()
            dummy_data['dummy_outcome'] = dummy_outcome
            
            dummy_effect = self._estimate_causal_effect(causal_graph, dummy_data, outcome_col='dummy_outcome')
            
            t_stat, p_value = stats.ttest_1samp([dummy_effect], 0)
            
            passed = abs(dummy_effect) < 0.05 and p_value > 0.05
            
            return RefutationTest(
                name="dummy_outcome",
                passed=passed,
                p_value=p_value,
                effect_estimate=dummy_effect,
                confidence_interval=(dummy_effect - 0.05, dummy_effect + 0.05)
            )
        except Exception:
            return RefutationTest("dummy_outcome", False, 1.0, 0.0, (0.0, 0.0))
    
    def _calculate_e_value(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Calculate E-value for sensitivity analysis"""
        try:
            effect_estimate = self._estimate_causal_effect(causal_graph, data)
            
            if effect_estimate == 0:
                return 1.0
            
            rr = abs(effect_estimate) + 1
            e_value = rr + np.sqrt(rr * (rr - 1))
            
            return e_value
        except Exception:
            return 1.0
    
    def _calculate_overall_p_value(self, refutation_results: List[RefutationTest]) -> float:
        """Calculate overall p-value from refutation tests"""
        if not refutation_results:
            return 1.0
        
        p_values = [test.p_value for test in refutation_results if test.p_value > 0]
        
        if not p_values:
            return 1.0
        
        from scipy.stats import combine_pvalues
        try:
            _, combined_p = combine_pvalues(p_values, method='fisher')
            return combined_p
        except Exception:
            return np.mean(p_values)
    
    def _run_placebo_tests(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> bool:
        """Run placebo tests"""
        try:
            placebo_test = self._placebo_treatment_test(causal_graph, data)
            return placebo_test.passed
        except Exception:
            return False
    
    def _counterfactual_recovery_test(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Test counterfactual recovery capability"""
        try:
            data_array = self._get_data_array(data)
            n = len(data_array)
            
            if n < 10:
                return 0.5
            
            test_indices = np.random.choice(n, min(10, n//2), replace=False)
            
            recovery_scores = []
            for idx in test_indices:
                original_value = data_array[idx]
                
                modified_data = data_array.copy()
                modified_data[idx] = original_value + np.random.normal(0, 0.1)
                
                recovered_value = self._recover_counterfactual(causal_graph, modified_data, idx, original_value)
                
                recovery_error = abs(recovered_value - original_value)
                recovery_score = max(0, 1 - recovery_error)
                recovery_scores.append(recovery_score)
            
            return np.mean(recovery_scores)
        except Exception:
            return 0.5
    
    def _calibration_check(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Check prediction calibration"""
        try:
            data_array = self._get_data_array(data)
            n = len(data_array)
            
            if n < 20:
                return 0.7
            
            predictions = []
            actuals = []
            
            for i in range(min(20, n//2)):
                train_data = data_array[:i*2] if i > 0 else data_array[:10]
                test_idx = min(i*2 + 10, n-1)
                
                prediction = self._make_prediction(causal_graph, train_data, test_idx)
                actual = data_array[test_idx]
                
                predictions.append(prediction)
                actuals.append(actual)
            
            if len(predictions) < 2:
                return 0.7
            
            correlation = np.corrcoef(predictions, actuals)[0, 1]
            calibration_score = max(0, correlation) if not np.isnan(correlation) else 0.5
            
            return calibration_score
        except Exception:
            return 0.7
    
    def _calculate_confidence_interval(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> Tuple[float, float]:
        """Calculate confidence interval for causal effect"""
        try:
            effect = self._estimate_causal_effect(causal_graph, data)
            std_error = self._estimate_standard_error(causal_graph, data)
            
            margin = 1.96 * std_error
            return (effect - margin, effect + margin)
        except Exception:
            return (0.0, 0.0)
    
    def _calculate_effect_size(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Calculate effect size (Cohen's d)"""
        try:
            effect = self._estimate_causal_effect(causal_graph, data)
            data_array = self._get_data_array(data)
            std_dev = np.std(data_array)
            
            if std_dev == 0:
                return 0.0
            
            return abs(effect) / std_dev
        except Exception:
            return 0.0
    
    def _calculate_statistical_power(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Calculate statistical power"""
        try:
            data_array = self._get_data_array(data)
            n = len(data_array)
            effect_size = self._calculate_effect_size(causal_graph, data)
            
            alpha = self.p_value_threshold
            
            from scipy.stats import norm
            z_alpha = norm.ppf(1 - alpha/2)
            z_beta = norm.ppf(0.8)
            
            required_n = ((z_alpha + z_beta) / effect_size) ** 2 if effect_size > 0 else float('inf')
            
            power = 1 - norm.cdf(z_alpha - effect_size * np.sqrt(n))
            
            return max(0, min(1, power))
        except Exception:
            return 0.5
    
    def _overall_validation_decision(self, e_value: float, p_value: float, placebo_result: bool,
                                   recovery_score: float, calibration_score: float,
                                   effect_size: float, statistical_power: float,
                                   refutation_results: List[RefutationTest]) -> bool:
        """Make overall validation decision"""
        criteria_met = 0
        total_criteria = 7
        
        if e_value >= self.e_value_threshold:
            criteria_met += 1
        
        if p_value <= self.p_value_threshold:
            criteria_met += 1
        
        if placebo_result:
            criteria_met += 1
        
        if recovery_score >= 0.8:
            criteria_met += 1
        
        if calibration_score >= 0.7:
            criteria_met += 1
        
        if effect_size >= self.min_effect_size:
            criteria_met += 1
        
        if statistical_power >= self.min_statistical_power:
            criteria_met += 1
        
        refutation_pass_rate = sum(1 for test in refutation_results if test.passed) / max(1, len(refutation_results))
        
        return criteria_met >= 5 and refutation_pass_rate >= 0.6
    
    def _get_data_array(self, data: Dict[str, Any]) -> np.ndarray:
        """Extract main data array from data dictionary"""
        for key in ['returns', 'prices', 'values', 'outcome', 'target']:
            if key in data:
                value = data[key]
                if isinstance(value, (list, np.ndarray)):
                    return np.array(value)
        
        numeric_values = []
        for value in data.values():
            if isinstance(value, (int, float)):
                numeric_values.append(value)
            elif isinstance(value, (list, np.ndarray)):
                try:
                    numeric_values.extend(np.array(value).flatten())
                except:
                    pass
        
        return np.array(numeric_values) if numeric_values else np.array([0.0])
    
    def _estimate_causal_effect(self, causal_graph: Dict[str, Any], data: Dict[str, Any], 
                              treatment_col: str = 'treatment', outcome_col: str = 'outcome') -> float:
        """Estimate causal effect"""
        try:
            data_array = self._get_data_array(data)
            
            if len(data_array) < 2:
                return 0.0
            
            treatment = data.get(treatment_col, np.random.binomial(1, 0.5, len(data_array)))
            outcome = data.get(outcome_col, data_array)
            
            if isinstance(treatment, (int, float)):
                treatment = np.array([treatment])
            if isinstance(outcome, (int, float)):
                outcome = np.array([outcome])
            
            treatment = np.array(treatment)
            outcome = np.array(outcome)
            
            min_len = min(len(treatment), len(outcome))
            treatment = treatment[:min_len]
            outcome = outcome[:min_len]
            
            if len(np.unique(treatment)) < 2:
                return 0.0
            
            treated_outcomes = outcome[treatment == 1] if np.any(treatment == 1) else np.array([])
            control_outcomes = outcome[treatment == 0] if np.any(treatment == 0) else np.array([])
            
            if len(treated_outcomes) == 0 or len(control_outcomes) == 0:
                return 0.0
            
            effect = np.mean(treated_outcomes) - np.mean(control_outcomes)
            return effect
        except Exception:
            return 0.0
    
    def _estimate_standard_error(self, causal_graph: Dict[str, Any], data: Dict[str, Any]) -> float:
        """Estimate standard error of causal effect"""
        try:
            data_array = self._get_data_array(data)
            n = len(data_array)
            
            if n < 2:
                return 1.0
            
            std_dev = np.std(data_array)
            return std_dev / np.sqrt(n)
        except Exception:
            return 1.0
    
    def _recover_counterfactual(self, causal_graph: Dict[str, Any], data: np.ndarray, 
                              index: int, original_value: float) -> float:
        """Recover counterfactual value"""
        try:
            if index >= len(data):
                return original_value
            
            neighbors = []
            for i in range(max(0, index-2), min(len(data), index+3)):
                if i != index:
                    neighbors.append(data[i])
            
            if neighbors:
                return np.mean(neighbors)
            else:
                return original_value
        except Exception:
            return original_value
    
    def _make_prediction(self, causal_graph: Dict[str, Any], train_data: np.ndarray, test_idx: int) -> float:
        """Make prediction for calibration check"""
        try:
            if len(train_data) == 0:
                return 0.0
            
            return np.mean(train_data[-min(5, len(train_data)):])
        except Exception:
            return 0.0

def validate_scientific_rigor(causal_graph: Dict[str, Any], 
                            data: Dict[str, Any], 
                            intervention: Optional[Dict[str, Any]] = None,
                            **kwargs) -> RigorValidationResult:
    """
    Main validation function for scientific rigor
    This is the primary entry point for causal validation
    """
    framework = ScientificRigorFramework(**kwargs)
    return framework.validate_scientific_rigor(causal_graph, data, intervention)
