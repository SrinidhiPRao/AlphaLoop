import numpy as np
import pandas as pd


def xAbs(x: pd.Series) -> pd.Series:
    return x.abs()


def xLog(x: pd.Series) -> pd.Series:
    return np.log(x.replace(0, np.nan))


def Add(x: pd.Series, y: pd.Series) -> pd.Series:
    return x + y


def Sub(x: pd.Series, y: pd.Series) -> pd.Series:
    return x - y


def Mul(x: pd.Series, y: pd.Series) -> pd.Series:
    return x * y


def Div(x: pd.Series, y: pd.Series) -> pd.Series:
    return x / y.replace(0, np.nan)


def Greater(x: pd.Series, y: pd.Series) -> pd.Series:
    return pd.concat([x, y], axis=1).max(axis=1)


def Less(x: pd.Series, y: pd.Series) -> pd.Series:
    return pd.concat([x, y], axis=1).min(axis=1)


def Ref(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").shift(t)


def Mean(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").rolling(t).mean().reset_index(level=0, drop=True)


def Med(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").rolling(t).median().reset_index(level=0, drop=True)


def Sum(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").rolling(t).sum().reset_index(level=0, drop=True)


def Std(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").rolling(t).std().reset_index(level=0, drop=True)


def Var(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").rolling(t).var().reset_index(level=0, drop=True)


def Max(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").rolling(t).max().reset_index(level=0, drop=True)


def Min(x: pd.Series, t: int) -> pd.Series:
    return x.groupby(level="ticker").rolling(t).min().reset_index(level=0, drop=True)


def Mad(x: pd.Series, t: int) -> pd.Series:
    def mad(arr):
        return np.mean(np.abs(arr - np.mean(arr)))

    return (
        x.groupby(level="ticker")
        .rolling(t)
        .apply(mad, raw=True)
        .reset_index(level=0, drop=True)
    )


def Delta(x: pd.Series, t: int) -> pd.Series:
    return x - Ref(x, t)


def WMA(x: pd.Series, t: int) -> pd.Series:
    weights = np.arange(1, t + 1)

    def wma(arr):
        return np.dot(arr, weights) / weights.sum()

    return (
        x.groupby(level="ticker")
        .rolling(t)
        .apply(wma, raw=True)
        .reset_index(level=0, drop=True)
    )


def EMA(x: pd.Series, t: int) -> pd.Series:
    return (
        x.groupby(level="ticker")
        .apply(lambda s: s.ewm(span=t, adjust=False).mean())
        .reset_index(level=0, drop=True)
    )


def Cov(x: pd.Series, y: pd.Series, t: int) -> pd.Series:
    df = pd.concat([x, y], axis=1)
    df.columns = ["x", "y"]

    return (
        df.groupby(level="ticker")
        .rolling(t)
        .cov()
        .iloc[0::2, 1]  # extract cov(x, y)
        .reset_index(level=0, drop=True)
    )


def Corr(x: pd.Series, y: pd.Series, t: int) -> pd.Series:
    df = pd.concat([x, y], axis=1)
    df.columns = ["x", "y"]

    return (
        df.groupby(level="ticker")
        .rolling(t)
        .corr()
        .iloc[0::2, 1]  # extract corr(x, y)
        .reset_index(level=0, drop=True)
    )
