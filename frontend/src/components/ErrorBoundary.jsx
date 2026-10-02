import { Component } from "react";

import { useI18n } from "../i18n";

function Fallback({ onRetry, compact }) {
  const { t } = useI18n();
  return (
    <div className={compact ? "alert alert-warn" : "card"} role="alert" style={compact ? undefined : { margin: 16 }}>
      <strong>{t("errors.loadTitle")}</strong>
      <p className="small" style={{ margin: "6px 0 10px" }}>
        {t("errors.loadBody")}
      </p>
      <button className="btn btn-sm btn-secondary" onClick={onRetry}>
        {t("common.retry")}
      </button>
    </div>
  );
}

/**
 * Catches render errors, most often a code chunk that couldn't be downloaded
 * (offline, or a new version was deployed), so one broken piece never blanks the app.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) this.setState({ error: null });
  }

  render() {
    if (!this.state.error) return this.props.children;
    const retry = () => {
      if (this.props.reloadOnRetry) window.location.reload();
      else this.setState({ error: null });
    };
    return <Fallback onRetry={retry} compact={this.props.compact} />;
  }
}
