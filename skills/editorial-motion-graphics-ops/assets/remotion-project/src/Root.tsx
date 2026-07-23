import React from 'react';
import {Composition} from 'remotion';
import {EditorialMotion} from './EditorialMotion';
import {motionSpec} from './motionSpec';

export const Root: React.FC = () => (
  <Composition
    id="EditorialMotion"
    component={EditorialMotion}
    durationInFrames={motionSpec.durationInFrames}
    fps={motionSpec.fps}
    width={motionSpec.width}
    height={motionSpec.height}
  />
);
