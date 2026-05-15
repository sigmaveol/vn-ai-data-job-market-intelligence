"""Salary prediction model (optional ML experiment — Phase 8)."""
import pandas as pd


class SalaryPredictor:
    def __init__(self):
        # TODO Phase 8: initialize XGBoost or RandomForest regressor
        pass

    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Encode categorical features (location, role, skills) for ML."""
        # TODO Phase 8: one-hot encode location, role; multi-hot encode skills
        raise NotImplementedError

    def train(self, df: pd.DataFrame) -> None:
        """Fit model on cleaned dataset with salary_min as target."""
        # TODO Phase 8: train_test_split → fit → log RMSE and R²
        raise NotImplementedError

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """Return predicted salary for input rows."""
        # TODO Phase 8: model.predict(prepare_features(df))
        raise NotImplementedError

    def feature_importance(self) -> pd.Series:
        """Return feature importance scores for interpretation."""
        # TODO Phase 8: model.feature_importances_ → pd.Series
        raise NotImplementedError
