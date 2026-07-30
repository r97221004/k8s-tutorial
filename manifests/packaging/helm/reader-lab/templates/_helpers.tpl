{{/*
Return the chart name, shortened to fit a DNS label.
*/}}
{{- define "reader-lab.name" -}}
{{- .Chart.Name | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Use fullnameOverride when supplied; otherwise combine the release and chart names.
*/}}
{{- define "reader-lab.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name (include "reader-lab.name" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}

{{/*
Stable labels used by selectors.
*/}}
{{- define "reader-lab.selectorLabels" -}}
app.kubernetes.io/name: {{ include "reader-lab.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
This helper deliberately accepts a dict rather than the root context directly:
  root:  the Helm root context
  extra: additional labels supplied by the user
*/}}
{{- define "reader-lab.labels" -}}
helm.sh/chart: {{ printf "%s-%s" .root.Chart.Name .root.Chart.Version }}
{{ include "reader-lab.selectorLabels" .root }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
{{- with .extra }}
{{ toYaml . }}
{{- end }}
{{- end }}
