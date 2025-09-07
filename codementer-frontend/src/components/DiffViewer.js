import React, { useContext } from 'react';
import ReactDiffViewer from 'react-diff-viewer-continued';
import { AppContext } from '../context/AppContext';

const DiffViewer = () => {
  const { code, finalCode } = useContext(AppContext);

  return (
    <ReactDiffViewer
      oldValue={code}
      newValue={finalCode}
      splitView={true}
      leftTitle="Original Code"
      rightTitle="Fixed Code"
      styles={{
        diffContainer: { fontSize: '14px', fontFamily: 'monospace' },
        title: { fontWeight: 'bold', color: 'inherit' },
        line: { lineHeight: '1.5' },
      }}
    />
  );
};

export default DiffViewer;